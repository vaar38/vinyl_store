import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

database_url = os.environ["DATABASE_URL"]
engine = create_engine(database_url)


class Base(DeclarativeBase):
    pass
