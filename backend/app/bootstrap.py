import argparse
import getpass

from app.db import SessionLocal
from app.models import Role, User
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Подготовка ролей и служебных аккаунтов")
    parser.add_argument("--email")
    parser.add_argument("--name", default="Сотрудник магазина")
    parser.add_argument("--role", choices=("admin", "staff"), default="admin")
    args = parser.parse_args()
    password = None
    if args.email:
        password = getpass.getpass("Пароль нового служебного аккаунта: ")
        if not 8 <= len(password) <= 128:
            parser.error("Длина пароля должна быть от 8 до 128 символов")
    with SessionLocal.begin() as db:
        roles = {}
        for code, name in (
            ("customer", "Покупатель"),
            ("staff", "Сотрудник"),
            ("admin", "Администратор"),
        ):
            role = db.query(Role).filter(Role.code == code).first()
            if role is None:
                role = Role(code=code, name=name)
                db.add(role)
                db.flush()
            roles[code] = role
        if args.email:
            if db.query(User).filter(User.email == args.email).first() is not None:
                parser.error("Аккаунт уже существует. Существующие права не изменены.")
            db.add(
                User(
                    email=args.email,
                    full_name=args.name,
                    password_hash=hash_password(password),
                    role_id=roles[args.role].id,
                )
            )
    print("Подготовка завершена")


if __name__ == "__main__":
    main()
