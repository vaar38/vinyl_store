from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db

from app.schemas.users import UserRegister, UserResponse

from app.models import User, Role

from app.security import hash_password

router = APIRouter()

@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    #находим пользователя
    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")

    #находим роль пользователя
    customer_role = db.query(Role).filter(Role.code == "customer").first()

    if customer_role is None:
        raise HTTPException(status_code=500, detail="Роль покупателя не настроена")

    user = User(
        role_id = customer_role.id,
        email = data.email,
        password_hash = hash_password(data.password),
        full_name = data.full_name,
        phone = data.phone
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(User).filter(User.email == data.email).first()
        if user is not None:
            raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
        raise
    db.refresh(user)
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone}
    
