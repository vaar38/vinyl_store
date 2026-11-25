from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    func,
    String,
)

from app.db import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    previous_status = Column(String(24))
    new_status = Column(String(24), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
