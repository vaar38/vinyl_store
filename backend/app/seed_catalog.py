"""Load the shop's starting catalogue without replacing existing records."""

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from app.db import SessionLocal
from app.models import Artist, Genre, Record, Role, StockMovement, User

# Album, artist, genre, release year, price in rubles.
CATALOG = [
    ("Good Kid, M.A.A.D City", "Kendrick Lamar", "Gangsta Rap", 2012, 5990),
    ("Damn.", "Kendrick Lamar", "Hip-Hop", 2017, 5990),
    ("To Pimp a Butterfly", "Kendrick Lamar", "Alternative Hip-Hop", 2015, 5490),
    ("Man on the Moon: The End of Day", "Kid Cudi", "Alternative Hip-Hop", 2009, 5990),
    ("Take Care", "Drake", "Hip-Hop", 2011, 5490),
    ("Barter 6", "Young Thug", "Trap", 2015, 5490),
    ("LIVE.LOVE.A$AP", "A$AP Rocky", "Cloud Rap", 2011, 5490),
    ("LONG.LIVE.A$AP", "A$AP Rocky", "Cloud Rap", 2013, 5490),
    ("Stankonia", "OutKast", "Alternative Hip-Hop", 2000, 5990),
    ("Utopia", "Travis Scott", "Trap", 2023, 3490),
    ("Astroworld", "Travis Scott", "Trap", 2018, 5490),
    ("Chicken Talk", "Gucci Mane", "Trap", 2006, 3490),
    (
        "\u0411\u0430\u0441\u0442\u0430/\u0413\u0443\u0444",
        "\u0411\u0430\u0441\u0442\u0430 / \u0413\u0443\u0444",
        "Hip-Hop",
        2010,
        3990,
    ),
    ("2 DAYS NO LEAN", "Heronwater", "Trap", 2022, 1490),
    ("NO COMMERCIAL LYRICS", "Heronwater", "Trap", 2023, 1990),
    ("Cruiser Aurora", "FRIENDLY THUG 52 NGG", "Hip-Hop", 2022, 1990),
    ("Life of a Don", "Don Toliver", "Trap", 2021, 4990),
    ("Heaven or Hell", "Don Toliver", "Trap", 2020, 4490),
    ("Donny Womack", "Don Toliver", "Hip-Hop", 2018, 2990),
    ("Goodbye & Good Riddance", "Juice WRLD", "Hip-Hop", 2018, 4490),
    ("Meet the Woo", "Pop Smoke", "Drill", 2019, 3490),
    ("Die a Legend", "Polo G", "Hip-Hop", 2019, 3090),
    ("SremmLife", "Rae Sremmurd", "Trap", 2015, 3990),
    ("Eternal Atake", "Lil Uzi Vert", "Trap", 2020, 3490),
    ("2014 Forest Hills Drive", "J. Cole", "Hip-Hop", 2014, 5490),
    ("Whole Lotta Red", "Playboi Carti", "Trap", 2020, 4490),
    ("Savage Mode", "21 Savage & Metro Boomin", "Trap", 2016, 4490),
    ("Return to the 36 Chambers: The Dirty Version", "Ol' Dirty Bastard", "Hip-Hop", 1995, 4490),
    ("Tha Carter II", "Lil Wayne", "Hip-Hop", 2005, 4490),
    ("The Carter III", "Lil Wayne", "Hip-Hop", 2008, 5990),
    ("The Slim Shady LP", "Eminem", "Hip-Hop", 1999, 5490),
    ("The Marshall Mathers LP", "Eminem", "Hip-Hop", 2000, 5990),
    ("The Blueprint", "Jay-Z", "Hip-Hop", 2001, 5490),
    ("Donda", "Kanye West", "Hip-Hop", 2021, 5990),
    ("Watch the Throne", "Jay-Z & Kanye West", "Hip-Hop", 2011, 4990),
    ("The College Dropout", "Kanye West", "Hip-Hop", 2004, 3990),
    ("Late Registration", "Kanye West", "Hip-Hop", 2005, 4490),
    ("Yeezus", "Kanye West", "Hip-Hop", 2013, 5490),
    ("My Beautiful Dark Twisted Fantasy", "Kanye West", "Hip-Hop", 2010, 5990),
    ("Mystic Stylez", "Three 6 Mafia", "Trap", 1995, 4490),
    ("Get Rich or Die Tryin", "50 Cent", "Gangsta Rap", 2003, 5490),
    ("Culture", "Migos", "Trap", 2017, 5490),
    ("Straight Outta Compton", "N.W.A", "Gangsta Rap", 1988, 3990),
    ("The Chronic", "Dr. Dre", "Gangsta Rap", 1992, 4490),
    ("2001", "Dr. Dre", "Gangsta Rap", 1999, 4990),
    ("Finally Rich", "Chief Keef", "Drill", 2012, 5990),
    ("All Eyez on Me", "2Pac", "Gangsta Rap", 1996, 5490),
    ("The Infamous", "Mobb Deep", "Gangsta Rap", 1995, 5990),
    ("Illmatic", "Nas", "Boom Bap", 1994, 5990),
    ("DS2", "Future", "Trap", 2015, 5490),
    ("Enter the Wu-Tang (36 Chambers)", "Wu-Tang Clan", "Boom Bap", 1993, 5990),
    ("Ready to Die", "The Notorious B.I.G.", "Gangsta Rap", 1994, 5990),
]


def main():
    covers = {
        (item["artist"], item["album"]): item["cover_url"]
        for item in json.loads(
            Path(__file__).with_name("catalog_covers.json").read_text(encoding="utf-8")
        )
    }
    added = 0
    updated = 0
    skipped = 0
    with SessionLocal.begin() as db:
        # Serialize imports so simultaneous runs cannot create duplicate entries.
        db.execute(text("SELECT pg_advisory_xact_lock(8152047)"))
        actor = (
            db.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(Role.code == "admin", User.is_active.is_(True))
            .order_by(User.id)
            .first()
        )
        if actor is None:
            raise SystemExit("Create an administrator with app.bootstrap before importing.")
        for album, artist_name, genre_name, year, price in CATALOG:
            artist = db.query(Artist).filter(Artist.name == artist_name).first()
            if artist is None:
                artist = Artist(name=artist_name)
                db.add(artist)
                db.flush()
            if artist_name == "A$AP Rocky" and not artist.image_url:
                artist.image_url = "/images/artists/asap-rocky.jpg"
            existing = (
                db.query(Record)
                .filter(Record.artist_id == artist.id, Record.album == album)
                .first()
            )
            cover_url = covers.get((artist_name, album))
            if existing is not None:
                if not existing.cover_url and cover_url:
                    existing.cover_url = cover_url
                    updated += 1
                skipped += 1
                continue
            genre = db.query(Genre).filter(Genre.name == genre_name).first()
            if genre is None:
                genre = Genre(name=genre_name)
                db.add(genre)
                db.flush()
            record = Record(
                album=album,
                artist_id=artist.id,
                genre_id=genre.id,
                cover_url=cover_url,
                release_year=year,
                price=Decimal(price),
                available_stock=5,
                is_active=True,
            )
            db.add(record)
            db.flush()
            db.add(StockMovement(
                record_id=record.id,
                actor_id=actor.id,
                quantity_delta=5,
                reason="initial",
            ))
            added += 1
    print(f"Added: {added}; already present: {skipped}; covers updated: {updated}")


if __name__ == "__main__":
    main()
