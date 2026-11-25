from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, String, CheckConstraint

from app.db import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("records.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    reason = Column(String(24), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    __table_args__ = (
        CheckConstraint("quantity_delta <> 0", name="ck_stock_movements_delta_nonzero"),
    )
