from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.security import get_current_user

from app.models import User, Cart, CartItem, Record

from app.schemas.cart import CartItemCreate, CartItemUpdate

from app.db import get_db

router = APIRouter()


@router.post("/cart/items")
def add_cart_item(
    data: CartItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = (
        db.query(Record)
        .filter(Record.id == data.record_id)
        .filter(Record.is_active.is_(True))
        .first()
    )

    if record is None:
        raise HTTPException(status_code=404, detail="Пластинка не найдена")

    db.query(User).filter(User.id == user.id).with_for_update().one()

    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.flush()

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id)
        .filter(CartItem.record_id == record.id)
        .first()
    )

    if cart_item is None:
        cart_item = CartItem(cart_id=cart.id, record_id=record.id, quantity=data.quantity)
        db.add(cart_item)

    else:
        cart_item.quantity += data.quantity

    db.commit()
    db.refresh(cart_item)
    return {
        "record_id": cart_item.record_id,
        "quantity": cart_item.quantity,
    }


@router.get("/cart")
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        return []

    rows = (
        db.query(CartItem, Record)
        .join(Record, Record.id == CartItem.record_id)
        .filter(CartItem.cart_id == cart.id)
        .all()
    )

    result = []
    for cart_item, record in rows:
        item = {
            "record_id": record.id,
            "album": record.album,
            "price": record.price,
            "quantity": cart_item.quantity,
            "available_stock": record.available_stock,
            "is_active": record.is_active,
        }
        result.append(item)

    return result


@router.patch("/cart/items/{record_id}")
def update_cart_item(
    record_id: int,
    data: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(User).filter(User.id == user.id).with_for_update().one()
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.record_id == record_id)
        .first()
    )

    if cart_item is None:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    cart_item.quantity = data.quantity
    db.commit()
    db.refresh(cart_item)
    return {
        "record_id": cart_item.record_id,
        "quantity": cart_item.quantity,
    }


@router.delete("/cart/items/{record_id}", status_code=204)
def delete_cart_item(
    record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.query(User).filter(User.id == user.id).with_for_update().one()
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()

    if cart is None:
        raise HTTPException(status_code=404, detail="Корзина не найдена")

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.record_id == record_id)
        .first()
    )
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    db.delete(cart_item)
    db.commit()
