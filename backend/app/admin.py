from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Artist, Genre, Record, StockMovement, User
from app.permissions import require_admin
from app.schemas.management import ArtistData, GenreData, RecordData, RecordUpdate

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def record_data(record):
    return {
        "id": record.id,
        "artist_id": record.artist_id,
        "genre_id": record.genre_id,
        "album": record.album,
        "description": record.description,
        "cover_url": record.cover_url,
        "release_year": record.release_year,
        "price": record.price,
        "available_stock": record.available_stock,
        "is_active": record.is_active,
        "updated_at": record.updated_at,
    }


@router.get("/records")
def get_records(db: Session = Depends(get_db)):
    return [record_data(record) for record in db.query(Record).order_by(Record.id).all()]


def check_references(data, db):
    if db.get(Artist, data.artist_id) is None or db.get(Genre, data.genre_id) is None:
        raise HTTPException(status_code=422, detail="Исполнитель или жанр не найден")


@router.post("/records", status_code=201)
def create_record(
    data: RecordData,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_references(data, db)
    record = Record(**data.model_dump())
    db.add(record)
    db.flush()
    if record.available_stock:
        db.add(
            StockMovement(
                record_id=record.id,
                actor_id=user.id,
                quantity_delta=record.available_stock,
                reason="initial",
            )
        )
    db.commit()
    db.refresh(record)
    return record_data(record)


@router.put("/records/{record_id}")
def update_record(
    record_id: int,
    data: RecordUpdate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    record = db.query(Record).filter(Record.id == record_id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Пластинка не найдена")
    check_references(data, db)
    if record.updated_at != data.expected_updated_at:
        raise HTTPException(
            status_code=409,
            detail="Пластинка изменена. Обновите список и повторите правки.",
        )
    delta = data.available_stock - record.available_stock
    for field, value in data.model_dump(exclude={"expected_updated_at"}).items():
        setattr(record, field, value)
    if delta:
        db.add(
            StockMovement(
                record_id=record.id,
                actor_id=user.id,
                quantity_delta=delta,
                reason="adjustment",
            )
        )
    db.commit()
    db.refresh(record)
    return record_data(record)


@router.delete("/records/{record_id}", status_code=204)
def archive_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Пластинка не найдена")
    record.is_active = False
    db.commit()


@router.get("/artists")
def get_artists(db: Session = Depends(get_db)):
    return [
        {
            "id": artist.id,
            "name": artist.name,
            "country_code": artist.country_code,
            "biography": artist.biography,
            "image_url": artist.image_url,
        }
        for artist in db.query(Artist).order_by(Artist.name).all()
    ]


@router.post("/artists", status_code=201)
def create_artist(data: ArtistData, db: Session = Depends(get_db)):
    artist = Artist(**data.model_dump())
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return {"id": artist.id, **data.model_dump()}


@router.put("/artists/{artist_id}")
def update_artist(artist_id: int, data: ArtistData, db: Session = Depends(get_db)):
    artist = db.get(Artist, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Исполнитель не найден")
    for field, value in data.model_dump().items():
        setattr(artist, field, value)
    db.commit()
    return {"id": artist.id, **data.model_dump()}


@router.get("/genres")
def get_genres(db: Session = Depends(get_db)):
    return [
        {"id": genre.id, "name": genre.name, "description": genre.description}
        for genre in db.query(Genre).order_by(Genre.name).all()
    ]


def save_genre(genre, data, db):
    for field, value in data.model_dump().items():
        setattr(genre, field, value)
    db.add(genre)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Жанр с таким названием уже существует")
    db.refresh(genre)
    return {"id": genre.id, **data.model_dump()}


@router.post("/genres", status_code=201)
def create_genre(data: GenreData, db: Session = Depends(get_db)):
    return save_genre(Genre(), data, db)


@router.put("/genres/{genre_id}")
def update_genre(genre_id: int, data: GenreData, db: Session = Depends(get_db)):
    genre = db.get(Genre, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Жанр не найден")
    return save_genre(genre, data, db)
