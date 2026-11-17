from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)

from app.db import Base


class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False)
    genre_id = Column(Integer, ForeignKey("genres.id"), nullable=False)
    album = Column(Text, nullable=False)
    description = Column(Text)
    cover_url = Column(Text)
    release_year = Column(SmallInteger)
    price = Column(Numeric(12, 2), nullable=False)
    available_stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_records_price_positive"),
        CheckConstraint("available_stock >= 0", name="ck_records_stock_nonnegative"),
    )