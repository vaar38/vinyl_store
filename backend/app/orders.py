from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.db import get_db
from app.security import get_current_user

from app.schemas.orders import OrderCreate

from app.models import User, Cart, CartItem, Record, Order, OrderItem, StockMovement, OrderStatusHistory

from decimal import Decimal

router = APIRouter()

@router.post("/orders", status_code=201)
def create_order(
    data: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(User).filter(User.id == user.id).with_for_update().one()
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    records_ids = [item.record_id for item in cart_items]

    records = db.query(Record).filter(Record.id.in_(records_ids)).order_by(Record.id).with_for_update().all()

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
        user_id = user.id,
        recipient_name = data.recipient_name,
        recipient_phone = data.recipient_phone,
        delivery_address = data.delivery_address,
        delivery_comment = data.delivery_comment,
        delivery_fee =  delivery_fee,
        total_amount = total_amount
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        record = records_by_id.get(item.record_id)

        order_item = OrderItem(
            order_id = order.id,
            record_id = record.id,
            quantity = item.quantity,
            unit_price = record.price
        )

        db.add(order_item)
        record.available_stock -= item.quantity

        stock_movement = StockMovement(
            record_id = record.id,
            order_id = order.id,
            actor_id = user.id,
            quantity_delta = -item.quantity,
            reason = "reserve",
        )

        db.add(stock_movement)

    order_status_history = OrderStatusHistory(
        order_id = order.id,
        actor_id = user.id,
        previous_status = None,
        new_status = "created"
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
        "delivery_fee": order.delivery_fee
    }

    
        
