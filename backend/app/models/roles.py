from sqlalchemy import Column, Integer, String, Text

from app.db import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    code = Column(String(24), unique=True, nullable=False)
    name = Column(Text, nullable=False)
