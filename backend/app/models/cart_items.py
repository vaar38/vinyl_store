from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, CheckConstraint

from app.db import Base


class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id = Column(Integer, ForeignKey("carts.id"), primary_key=True)
    record_id = Column(Integer, ForeignKey("records.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
    added_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_quantity_nonnegative"),)
