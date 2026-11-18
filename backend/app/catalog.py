from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Record, Artist, Genre


router = APIRouter()


@router.get("/records")
def get_catalog(genre_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Record,Artist).join(Artist, Artist.id == Record.artist_id).filter(Record.is_active.is_(True))


    if genre_id is not None:
        query = query.filter(Record.genre_id == genre_id)

    records = query.all()
    result = []
    for record, artist in records:
        item = {
            "id": record.id,
            "album": record.album,
            "price": record.price,
            "available_stock": record.available_stock,
            "cover_url": record.cover_url,
            "artist": artist.name,
        }
        result.append(item)

    return result

@router.get("/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(Record, Artist, Genre)
        .join(Artist, Artist.id == Record.artist_id)
        .join(Genre, Genre.id == Record.genre_id)
        .filter(Record.id == record_id, Record.is_active.is_(True))
        .first()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Пластинка не найдена")

    record, artist, genre = row
    item = {
        "id": record.id,
        "album": record.album,
        "price": record.price,
        "available_stock": record.available_stock,
        "description": record.description,
        "cover_url": record.cover_url,
        "release_year": record.release_year,
        "artist": artist.name,
        "genre": genre.name,
    }

    return item