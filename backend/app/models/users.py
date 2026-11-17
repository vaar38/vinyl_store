from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    phone = Column(String(32))
    token_version = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )