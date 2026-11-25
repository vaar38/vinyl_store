from sqlalchemy import Column, Integer, ForeignKey, Numeric, CheckConstraint

from app.db import Base


class OrderItem(Base):
    __tablename__ = "order_items"
    order_id = Column(Integer, ForeignKey("orders.id"), primary_key=True)
    record_id = Column(Integer, ForeignKey("records.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quantity_nonnullable"),
        CheckConstraint("unit_price > 0", name="ck_unit_price_nonnullable"),
    )
