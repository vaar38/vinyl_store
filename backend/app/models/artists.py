from sqlalchemy import CHAR, Column, Integer, Text

from app.db import Base


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    country_code = Column(CHAR(2))
    biography = Column(Text)
    image_url = Column(Text)
