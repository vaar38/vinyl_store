import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import Base, engine as application_engine, get_db
from app.main import app
from app.models import (
    Artist, Cart, CartItem, Genre, Order, OrderItem, OrderStatusHistory,
    Record, Role, StockMovement, User,
)
from app.security import create_access_token, hash_password


@pytest.fixture
def shop():
    if application_engine.dialect.name != "postgresql":
        pytest.fail("Для проверки блокировок требуется PostgreSQL")
    schema = "test_vinyl_" + uuid.uuid4().hex
    with application_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = create_engine(
        application_engine.url, connect_args={"options": f"-csearch_path={schema}"},
    )
    sessions = sessionmaker(bind=test_engine)
    Base.metadata.create_all(test_engine)

    def session_dependency():
        with sessions() as db:
            try:
                yield db
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = session_dependency
    users = {}
    try:
        with sessions.begin() as db:
            for code in ("customer", "staff", "admin"):
                role = Role(code=code, name=code)
                db.add(role)
                db.flush()
                names = ("buyer", "other") if code == "customer" else (code,)
                for name in names:
                    user = User(
                        email=f"{name}@example.com", full_name=name, role_id=role.id,
                        password_hash=hash_password("TestPassword123"),
                    )
                    db.add(user)
                    db.flush()
                    users[name] = user.id
            db.add(Artist(name="Test artist"))
            db.add(Genre(name="Test genre"))
            db.flush()
            db.add(Record(
                artist_id=1, genre_id=1, album="Test album",
                price=Decimal("100.25"), available_stock=1,
            ))
        with TestClient(app) as client:
            yield client, sessions, users
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
        with application_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def headers(users, name="buyer"):
    return {"Authorization": "Bearer " + create_access_token(users[name])}


def checkout(client, users, name="buyer"):
    return client.post("/api/orders", headers=headers(users, name), json={
        "recipient_name": "Покупатель", "recipient_phone": "+79990000000",
        "delivery_address": "Москва, улица Тестовая, 1",
    })


def add(client, users, name="buyer", quantity=1):
    return client.post(
        "/api/cart/items", headers=headers(users, name),
        json={"record_id": 1, "quantity": quantity},
    )


def test_registration_login_and_profile(shop):
    client, sessions, users = shop
    data = {
        "email": "new@example.com", "password": "TestPassword123", "full_name": "Новый",
    }
    response = client.post("/api/auth/register", json=data)
    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert client.post("/api/auth/register", json=data).status_code == 409
    assert client.post("/api/auth/login", json={
        "email": data["email"], "password": "incorrect",
    }).status_code == 401
    response = client.post("/api/auth/login", json=data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert client.get("/api/users/me", headers={
        "Authorization": "Bearer " + token,
    }).json()["email"] == data["email"]


def test_catalog_and_validation(shop):
    client, sessions, users = shop
    assert len(client.get("/api/records?q=ALBUM&genre_id=1").json()) == 1
    assert client.get("/api/records?q=absent").json() == []
    assert client.get("/api/records/9999").status_code == 404
    with sessions.begin() as db:
        db.get(Record, 1).is_active = False
    assert client.get("/api/records/1").status_code == 404
    assert add(client, users).status_code == 404
    assert client.post("/api/cart/items", headers=headers(users), json={
        "record_id": 1, "quantity": 0,
    }).status_code == 422


def test_cart_and_owner_isolation(shop):
    client, sessions, users = shop
    assert add(client, users).json()["quantity"] == 1
    assert add(client, users).json()["quantity"] == 2
    assert client.get("/api/cart", headers=headers(users, "other")).json() == []
    assert client.patch("/api/cart/items/1", headers=headers(users), json={
        "quantity": 1,
    }).json()["quantity"] == 1
    assert client.delete("/api/cart/items/1", headers=headers(users, "other")).status_code == 404
    assert client.delete("/api/cart/items/1", headers=headers(users)).status_code == 204
    assert client.get("/api/cart", headers=headers(users)).json() == []
    with sessions() as db:
        assert db.get(Record, 1).available_stock == 1


def test_order_snapshot_and_repeated_cancel(shop):
    client, sessions, users = shop
    add(client, users)
    response = checkout(client, users)
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert Decimal(str(response.json()["total_amount"])) == Decimal("100.25")
    assert client.get("/api/cart", headers=headers(users)).json() == []
    with sessions.begin() as db:
        db.get(Record, 1).price = Decimal("500.00")
        assert db.get(Record, 1).available_stock == 0
    detail = client.get(f"/api/orders/{order_id}", headers=headers(users)).json()
    assert Decimal(str(detail["items"][0]["unit_price"])) == Decimal("100.25")
    assert client.get(f"/api/orders/{order_id}", headers=headers(users, "other")).status_code == 404
    assert client.post(f"/api/orders/{order_id}/cancel", headers=headers(users, "other")).status_code == 404
    for _ in range(2):
        assert client.post(
            f"/api/orders/{order_id}/cancel", headers=headers(users),
        ).json()["status"] == "cancelled"
    with sessions() as db:
        assert db.get(Record, 1).available_stock == 1
        assert db.query(StockMovement).count() == 2
        assert db.query(OrderStatusHistory).count() == 2


def test_atomic_order_failure(shop):
    client, sessions, users = shop
    with sessions.begin() as db:
        db.add(Record(
            id=2, artist_id=1, genre_id=1, album="Unavailable",
            price=10, available_stock=0,
        ))
    add(client, users)
    client.post("/api/cart/items", headers=headers(users), json={"record_id": 2})
    assert checkout(client, users).status_code == 409
    with sessions() as db:
        assert db.query(Order).count() == 0
        assert db.get(Record, 1).available_stock == 1
        assert db.query(CartItem).count() == 2
        assert db.query(StockMovement).count() == 0


def test_last_record_concurrent_checkout(shop):
    client, sessions, users = shop
    add(client, users, "buyer")
    add(client, users, "other")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda name: checkout(client, users, name), ["buyer", "other"]))
    assert sorted(response.status_code for response in responses) == [201, 409]
    with sessions() as db:
        assert db.query(Order).count() == 1
        assert db.query(OrderItem).count() == 1
        assert db.get(Record, 1).available_stock == 0


def test_concurrent_cart_add(shop):
    client, sessions, users = shop
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: add(client, users), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    with sessions() as db:
        assert db.query(Cart).count() == 1
        assert db.query(CartItem).one().quantity == 2


def test_roles_and_delivery_transitions(shop):
    client, sessions, users = shop
    assert client.get("/api/admin/records", headers=headers(users)).status_code == 403
    assert client.get("/api/staff/orders", headers=headers(users)).status_code == 403
    assert client.get("/api/admin/records", headers=headers(users, "staff")).status_code == 403
    assert client.get("/api/admin/records", headers=headers(users, "admin")).status_code == 200
    add(client, users)
    order_id = checkout(client, users).json()["id"]
    url = f"/api/staff/orders/{order_id}/status"
    assert client.patch(url, headers=headers(users, "staff"), json={
        "status": "delivered",
    }).status_code == 409
    for status in ("assembling", "ready", "shipped", "delivered"):
        assert client.patch(url, headers=headers(users, "staff"), json={
            "status": status,
        }).json()["status"] == status
    assert client.post(f"/api/orders/{order_id}/cancel", headers=headers(users)).status_code == 409


def test_admin_catalog_and_stock_journal(shop):
    client, sessions, users = shop
    data = {
        "artist_id": 1, "genre_id": 1, "album": "New record", "price": "42.50",
        "available_stock": 3,
    }
    response = client.post("/api/admin/records", headers=headers(users, "admin"), json=data)
    assert response.status_code == 201
    record_id = response.json()["id"]
    data["available_stock"] = 7
    data["expected_updated_at"] = response.json()["updated_at"]
    assert client.put(
        f"/api/admin/records/{record_id}", headers=headers(users, "admin"), json=data,
    ).status_code == 200
    with sessions() as db:
        movements = db.query(StockMovement).filter(StockMovement.record_id == record_id).all()
        assert sum(item.quantity_delta for item in movements) == 7
    assert client.delete(
        f"/api/admin/records/{record_id}", headers=headers(users, "admin"),
    ).status_code == 204
    assert client.get(f"/api/records/{record_id}").status_code == 404


def test_token_errors_and_disabled_account(shop):
    from datetime import datetime, timedelta, timezone
    import jwt
    from app.security import secret_key

    client, sessions, users = shop
    for token in (
        "invalid",
        jwt.encode({"sub": str(users["buyer"])}, secret_key, algorithm="HS256"),
        jwt.encode({
            "sub": str(users["buyer"]),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }, secret_key, algorithm="HS256"),
    ):
        assert client.get("/api/users/me", headers={
            "Authorization": "Bearer " + token,
        }).status_code == 401
    with sessions.begin() as db:
        db.get(User, users["buyer"]).is_active = False
    assert client.get("/api/users/me", headers=headers(users)).status_code == 403


def test_repeated_concurrent_cancel(shop):
    client, sessions, users = shop
    add(client, users)
    order_id = checkout(client, users).json()["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda _: client.post(
                f"/api/orders/{order_id}/cancel", headers=headers(users),
            ), range(2),
        ))
    assert [response.status_code for response in responses] == [200, 200]
    with sessions() as db:
        assert db.get(Record, 1).available_stock == 1
        assert db.query(StockMovement).filter(StockMovement.reason == "cancel").count() == 1


def test_cancel_competes_with_shipping(shop):
    client, sessions, users = shop
    add(client, users)
    order_id = checkout(client, users).json()["id"]
    for status in ("assembling", "ready"):
        client.patch(
            f"/api/staff/orders/{order_id}/status",
            headers=headers(users, "staff"), json={"status": status},
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        cancel = pool.submit(
            client.post, f"/api/orders/{order_id}/cancel", headers=headers(users),
        )
        ship = pool.submit(
            client.patch, f"/api/staff/orders/{order_id}/status",
            headers=headers(users, "staff"), json={"status": "shipped"},
        )
        assert sorted([cancel.result().status_code, ship.result().status_code]) == [200, 409]
    with sessions() as db:
        order = db.get(Order, order_id)
        assert order.status in ("cancelled", "shipped")
        assert db.get(Record, 1).available_stock == (1 if order.status == "cancelled" else 0)


def test_stale_admin_edit_cannot_restore_reserved_stock(shop):
    client, sessions, users = shop
    snapshot = client.get("/api/admin/records", headers=headers(users, "admin")).json()[0]
    add(client, users)
    assert checkout(client, users).status_code == 201
    snapshot["expected_updated_at"] = snapshot["updated_at"]
    snapshot["price"] = "200.00"
    response = client.put("/api/admin/records/1", headers=headers(users, "admin"), json=snapshot)
    assert response.status_code == 409
    with sessions() as db:
        assert db.get(Record, 1).available_stock == 0


def test_disabled_user_cannot_login(shop):
    client, sessions, users = shop
    with sessions.begin() as db:
        db.get(User, users["buyer"]).is_active = False
    response = client.post("/api/auth/login", json={
        "email": "buyer@example.com", "password": "TestPassword123",
    })
    assert response.status_code == 403
    assert "access_token" not in response.json()


def test_empty_checkout_creates_no_order(shop):
    client, sessions, users = shop
    assert checkout(client, users).status_code == 400
    add(client, users)
    client.delete("/api/cart/items/1", headers=headers(users))
    assert checkout(client, users).status_code == 400
    with sessions() as db:
        assert db.query(Order).count() == 0
        assert db.query(StockMovement).count() == 0
        assert db.get(Record, 1).available_stock == 1


def test_archived_record_blocks_existing_cart_checkout(shop):
    client, sessions, users = shop
    add(client, users)
    client.delete("/api/admin/records/1", headers=headers(users, "admin"))
    assert checkout(client, users).status_code == 409
    with sessions() as db:
        assert db.query(Order).count() == 0
        assert db.query(CartItem).one().quantity == 1
        assert db.get(Record, 1).available_stock == 1


def test_multi_item_order_uses_exact_decimal_total(shop):
    client, sessions, users = shop
    with sessions.begin() as db:
        db.get(Record, 1).available_stock = 3
        db.add(Record(
            id=2, artist_id=1, genre_id=1, album="Second album",
            price=Decimal("0.10"), available_stock=2,
        ))
    add(client, users, quantity=2)
    client.post("/api/cart/items", headers=headers(users), json={"record_id": 2, "quantity": 2})
    response = checkout(client, users)
    assert response.status_code == 201
    assert Decimal(str(response.json()["total_amount"])) == Decimal("200.70")
    assert Decimal(str(response.json()["delivery_fee"])) == Decimal("0")
    with sessions() as db:
        assert db.get(Record, 1).available_stock == 1
        assert db.get(Record, 2).available_stock == 0
        assert db.query(OrderItem).count() == 2
        assert db.query(CartItem).count() == 0


def test_order_list_contains_only_own_orders(shop):
    client, sessions, users = shop
    with sessions.begin() as db:
        db.get(Record, 1).available_stock = 2
    ids = {}
    for name in ("buyer", "other"):
        add(client, users, name)
        ids[name] = checkout(client, users, name).json()["id"]
    for name in ids:
        orders = client.get("/api/orders", headers=headers(users, name)).json()
        assert [order["id"] for order in orders] == [ids[name]]
    all_orders = client.get("/api/staff/orders", headers=headers(users, "staff")).json()
    assert {order["id"] for order in all_orders} == set(ids.values())


def test_repeated_staff_status_has_one_history_event(shop):
    client, sessions, users = shop
    add(client, users)
    order_id = checkout(client, users).json()["id"]
    for _ in range(2):
        response = client.patch(
            f"/api/staff/orders/{order_id}/status", headers=headers(users, "staff"),
            json={"status": "assembling"},
        )
        assert response.status_code == 200
    with sessions() as db:
        assert db.query(OrderStatusHistory).filter_by(order_id=order_id).count() == 2
        assert db.get(Record, 1).available_stock == 0


def test_invalid_catalog_reference_is_rejected_without_stock_movement(shop):
    client, sessions, users = shop
    response = client.post("/api/admin/records", headers=headers(users, "admin"), json={
        "album": "Missing artist", "artist_id": 9999, "genre_id": 1,
        "price": "100.00", "available_stock": 5,
    })
    assert response.status_code == 422
    with sessions() as db:
        assert db.query(Record).count() == 1
        assert db.query(StockMovement).count() == 0


def test_artist_photo_and_biography_in_record_details(shop):
    client, sessions, users = shop
    before = client.get("/api/records/1").json()
    assert before["artist_image_url"] is None
    assert before["artist_biography"] is None
    with sessions.begin() as db:
        artist = db.get(Artist, 1)
        artist.image_url = "/images/artists/example.jpg"
        artist.biography = "Artist biography"
    detail = client.get("/api/records/1").json()
    assert detail["artist_image_url"] == "/images/artists/example.jpg"
    assert detail["artist_biography"] == "Artist biography"
    assert detail["album"] == "Test album"


def test_cart_returns_current_record_cover(shop):
    client, sessions, users = shop
    add(client, users)
    assert client.get("/api/cart", headers=headers(users)).json()[0]["cover_url"] is None
    with sessions.begin() as db:
        db.get(Record, 1).cover_url = "/images/covers/example.jpg"
    item = client.get("/api/cart", headers=headers(users)).json()[0]
    assert item["cover_url"] == "/images/covers/example.jpg"
    assert item["record_id"] == 1
    assert item["quantity"] == 1
