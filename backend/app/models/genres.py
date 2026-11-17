from sqlalchemy import Column, Integer, Text

from app.db import Base


class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)