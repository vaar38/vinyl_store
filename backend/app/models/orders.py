from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    func,
    String,
    Text,
    Numeric,
    CheckConstraint
)

from app.db import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(24), nullable=False, default="created")
    recipient_name = Column(Text, nullable=False)
    recipient_phone = Column(String(32), nullable=False)
    delivery_address = Column(Text, nullable=False)
    delivery_comment = Column(Text)
    delivery_fee = Column(Numeric(12,2), nullable=False)
    total_amount = Column(Numeric(12,2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    shipped_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("delivery_fee >= 0", name="ck_delivery_fee_nonnegative"),
        CheckConstraint("total_amount > 0", name="ck_total_amount_nonnullable"),
    )