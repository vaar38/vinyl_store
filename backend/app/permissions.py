from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import get_current_user


def require_staff(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = db.get(Role, user.role_id)
    if role is None or role.code not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Требуется роль сотрудника")
    return user


def require_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = db.get(Role, user.role_id)
    if role is None or role.code != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль администратора")
    return user
