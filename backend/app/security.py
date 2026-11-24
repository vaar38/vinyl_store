from pwdlib import PasswordHash

import os
from pathlib import Path

from dotenv import load_dotenv

import jwt

from datetime import datetime, timedelta, timezone

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

from sqlalchemy.orm import Session

from app.db import get_db

from app.models import User


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
secret_key = os.environ["SECRET_KEY"]
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": str(user_id), "exp": expires_at}

    return jwt.encode(payload, secret_key, algorithm="HS256")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    if user.is_active == False:
        raise HTTPException(status_code=403, detail="Аккаунт отключён")

    return user