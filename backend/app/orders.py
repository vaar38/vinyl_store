from datetime import datetime, timezone

from app.models import Artist
from app.permissions import require_staff
from app.schemas.management import OrderStatusUpdate
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.db import get_db
from app.security import get_current_user

from app.schemas.orders import OrderCreate

from app.models import (
    User,
    Cart,
    CartItem,
    Record,
    Order,
    OrderItem,
    StockMovement,
    OrderStatusHistory,
)

from decimal import Decimal

router = APIRouter()


@router.post("/orders", status_code=201)
def create_order(
    data: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.query(User).filter(User.id == user.id).with_for_update().one()
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    records_ids = [item.record_id for item in cart_items]

    records = (
        db.query(Record)
        .filter(Record.id.in_(records_ids))
        .order_by(Record.id)
        .with_for_update()
        .all()
    )

    records_by_id = {record.id: record for record in records}

    for item in cart_items:
        record = records_by_id.get(item.record_id)

        if record is None or not record.is_active:
            raise HTTPException(status_code=409, detail="Пластинка недоступна")

        if record.available_stock < item.quantity:
            raise HTTPException(status_code=409, detail="Недостаточно пластинок в наличии")

    items_total = Decimal("0.00")

    for item in cart_items:
        record = records_by_id.get(item.record_id)
        items_total += record.price * item.quantity

    delivery_fee = Decimal("0.00")
    total_amount = items_total + delivery_fee

    order = Order(
        user_id=user.id,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
        delivery_address=data.delivery_address,
        delivery_comment=data.delivery_comment,
        delivery_fee=delivery_fee,
        total_amount=total_amount,
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        record = records_by_id.get(item.record_id)

        order_item = OrderItem(
            order_id=order.id, record_id=record.id, quantity=item.quantity, unit_price=record.price
        )

        db.add(order_item)
        record.available_stock -= item.quantity

        stock_movement = StockMovement(
            record_id=record.id,
            order_id=order.id,
            actor_id=user.id,
            quantity_delta=-item.quantity,
            reason="reserve",
        )

        db.add(stock_movement)

    order_status_history = OrderStatusHistory(
        order_id=order.id, actor_id=user.id, previous_status=None, new_status="created"
    )

    db.add(order_status_history)

    for item in cart_items:
        db.delete(item)

    db.commit()
    db.refresh(order)
    return {
        "id": order.id,
        "status": order.status,
        "total_amount": order.total_amount,
        "delivery_fee": order.delivery_fee,
    }


def order_summary(order):
    return {
        "id": order.id,
        "status": order.status,
        "total_amount": order.total_amount,
        "delivery_fee": order.delivery_fee,
        "created_at": order.created_at,
        "shipped_at": order.shipped_at,
        "delivered_at": order.delivered_at,
    }


def order_details(order, db):
    result = order_summary(order)
    result.update(
        {
            "recipient_name": order.recipient_name,
            "recipient_phone": order.recipient_phone,
            "delivery_address": order.delivery_address,
            "delivery_comment": order.delivery_comment,
        }
    )
    rows = (
        db.query(OrderItem, Record, Artist)
        .join(Record, Record.id == OrderItem.record_id)
        .join(Artist, Artist.id == Record.artist_id)
        .filter(OrderItem.order_id == order.id)
        .order_by(OrderItem.record_id)
        .all()
    )
    result["items"] = [
        {
            "record_id": item.record_id,
            "album": record.album,
            "artist": artist.name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
        }
        for item, record, artist in rows
    ]
    result["history"] = [
        {
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "created_at": event.created_at,
        }
        for event in db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.id)
        .all()
    ]
    return result


@router.get("/orders")
def get_orders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )
    return [order_summary(order) for order in orders]


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order_details(order, db)


def cancel_locked_order(order, actor, db):
    if order.status == "cancelled":
        return order_summary(order)
    if order.status not in ("created", "assembling", "ready"):
        raise HTTPException(status_code=409, detail="Заказ уже отправлен, отмена недоступна")
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    records = (
        db.query(Record)
        .filter(Record.id.in_([item.record_id for item in items]))
        .order_by(Record.id)
        .with_for_update()
        .all()
    )
    by_id = {record.id: record for record in records}
    for item in items:
        by_id[item.record_id].available_stock += item.quantity
        db.add(
            StockMovement(
                record_id=item.record_id,
                order_id=order.id,
                actor_id=actor.id,
                quantity_delta=item.quantity,
                reason="cancel",
            )
        )
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            actor_id=actor.id,
            previous_status=order.status,
            new_status="cancelled",
        )
    )
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return order_summary(order)


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(User).filter(User.id == user.id).with_for_update().one()
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == user.id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return cancel_locked_order(order, user, db)


@router.get("/staff/orders")
def staff_orders(
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    orders = db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).all()
    return [order_summary(order) for order in orders]


@router.get("/staff/orders/{order_id}")
def staff_order(
    order_id: int,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order_details(order, db)


@router.patch("/staff/orders/{order_id}/status")
def change_status(
    order_id: int,
    data: OrderStatusUpdate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status == data.status:
        return order_summary(order)
    transitions = {
        "created": "assembling",
        "assembling": "ready",
        "ready": "shipped",
        "shipped": "delivered",
    }
    if transitions.get(order.status) != data.status:
        raise HTTPException(status_code=409, detail="Недопустимый переход статуса")
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            actor_id=user.id,
            previous_status=order.status,
            new_status=data.status,
        )
    )
    order.status = data.status
    if data.status == "shipped":
        order.shipped_at = datetime.now(timezone.utc)
    if data.status == "delivered":
        order.delivered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order_summary(order)
