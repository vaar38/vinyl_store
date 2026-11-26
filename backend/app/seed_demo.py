"""Create fictional customers and a consistent order history for demonstrations."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.db import SessionLocal
from app.models import (
    Artist, Cart, CartItem, Order, OrderItem, OrderStatusHistory,
    Record, Role, StockMovement, User,
)
from app.security import hash_password

DEMO_PASSWORD = "VinylDemo2026!"
NAMES = [
    "Александр Смирнов", "Мария Волкова", "Дмитрий Соколов", "Анна Морозова",
    "Иван Кузнецов", "Екатерина Орлова", "Михаил Лебедев", "Софья Новикова",
    "Артём Попов", "Дарья Васильева", "Никита Павлов", "Полина Белова",
]
CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Екатеринбург",
    "Нижний Новгород", "Самара", "Новосибирск", "Пермь",
    "Воронеж", "Тула", "Ярославль", "Краснодар",
]
STATUSES = (
    ["delivered"] * 8 + ["shipped"] * 4 + ["ready"] * 3
    + ["assembling"] * 3 + ["created"] * 4 + ["cancelled"] * 2
)
PREFIX = "Демонстрационный заказ "
PATH = ["created", "assembling", "ready", "shipped", "delivered"]


def main():
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(8152048)"))
        existing = db.query(Order).filter(Order.delivery_comment.like(PREFIX + "%")).count()
        if existing:
            if existing != len(STATUSES):
                raise SystemExit("Incomplete demo dataset found; no changes made.")
            print("Demo orders already exist; no changes made.")
            return
        roles = {role.code: role for role in db.query(Role).all()}
        if not {"customer", "staff", "admin"} <= roles.keys():
            raise SystemExit("Run app.bootstrap first.")
        records = (
            db.query(Record).join(Artist, Record.artist_id == Artist.id)
            .filter(Record.is_active.is_(True)).order_by(Record.id).with_for_update().all()
        )
        if len(records) < 52:
            raise SystemExit("Import the 52-record catalogue first.")
        emails = [f"buyer{i + 1:02d}@example.com" for i in range(len(NAMES))]
        staff_email = "staff.demo@example.com"
        if db.query(User).filter(User.email.in_(emails + [staff_email])).first():
            raise SystemExit("A demo email is already in use; no changes made.")
        password_hash = hash_password(DEMO_PASSWORD)
        staff = User(
            email=staff_email, full_name="Алексей Миронов", role_id=roles["staff"].id,
            password_hash=password_hash, phone="+70000000999",
            created_at=now - timedelta(days=60), updated_at=now - timedelta(days=60),
        )
        db.add(staff)
        db.flush()
        buyers = []
        for i, name in enumerate(NAMES):
            joined = now - timedelta(days=55 - i * 2)
            buyer = User(
                email=emails[i], full_name=name, role_id=roles["customer"].id,
                password_hash=password_hash, phone=f"+70000000{101 + i:03d}",
                created_at=joined, updated_at=joined,
            )
            db.add(buyer)
            buyers.append(buyer)
        db.flush()
        for i, status in enumerate(STATUSES):
            buyer_index = i % len(buyers)
            buyer = buyers[buyer_index]
            # Older orders have finished; recent orders remain available to process.
            age = (24 - i if i < 18 else 1) if status != "cancelled" else 7
            created = now - timedelta(days=age, hours=2 + i % 6)
            items = [
                (records[(i * 2) % 52], 2 if i % 5 == 0 else 1),
                (records[(i * 2 + 1) % 52], 1),
            ]
            total = sum((record.price * quantity for record, quantity in items), Decimal("0"))
            order = Order(
                user_id=buyer.id, status=status, recipient_name=buyer.full_name,
                recipient_phone=buyer.phone,
                delivery_address=f"{CITIES[buyer_index]}, ул. Демонстрационная, "
                                 f"д. {10 + buyer_index}, кв. {20 + buyer_index}",
                delivery_comment=f"{PREFIX}{i + 1:02d}. Позвонить перед доставкой.",
                delivery_fee=Decimal("0.00"), total_amount=total, created_at=created,
            )
            db.add(order)
            db.flush()
            states = (["created", "assembling", "cancelled"] if status == "cancelled"
                      else PATH[:PATH.index(status) + 1])
            previous = None
            for step, state in enumerate(states):
                moment = created + timedelta(hours=step * 4)
                actor = buyer if step == 0 or state == "cancelled" else staff
                db.add(OrderStatusHistory(
                    order_id=order.id, actor_id=actor.id, previous_status=previous,
                    new_status=state, created_at=moment,
                ))
                if state == "shipped":
                    order.shipped_at = moment
                if state == "delivered":
                    order.delivered_at = moment
                previous = state
            for record, quantity in items:
                if record.available_stock < quantity:
                    raise SystemExit(f"Insufficient stock for {record.album}; import rolled back.")
                db.add(OrderItem(
                    order_id=order.id, record_id=record.id,
                    quantity=quantity, unit_price=record.price,
                ))
                record.available_stock -= quantity
                db.add(StockMovement(
                    record_id=record.id, order_id=order.id, actor_id=buyer.id,
                    quantity_delta=-quantity, reason="reserve", created_at=created,
                ))
                if status == "cancelled":
                    record.available_stock += quantity
                    db.add(StockMovement(
                        record_id=record.id, order_id=order.id, actor_id=buyer.id,
                        quantity_delta=quantity, reason="cancel",
                        created_at=created + timedelta(hours=8),
                    ))
        for i, buyer in enumerate(buyers):
            cart = Cart(user_id=buyer.id)
            db.add(cart)
            db.flush()
            if i < 4:
                db.add(CartItem(cart_id=cart.id, record_id=records[48 + i].id, quantity=1))
    print("Created: 12 buyers, 1 staff account, 24 orders, 12 carts.")
    print("Demo password: " + DEMO_PASSWORD)


if __name__ == "__main__":
    main()
