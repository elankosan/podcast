from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user, get_current_admin_user
from api.config import settings
from api.database import get_db
from api.models.user import User

router = APIRouter()


@router.get("/users")
async def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    users = db.query(User).all()
    return [{"id": str(u.id), "email": u.email, "name": u.name, "role": u.role} for u in users]


@router.post("/users")
async def create_user(user_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    from api.auth import get_password_hash
    from api.models.user import User
    db_user = User(
        email=user_data["email"],
        name=user_data["name"],
        hashed_password=get_password_hash(user_data["password"]),
        role=user_data.get("role", "host"),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": str(db_user.id), "email": db_user.email, "name": db_user.name, "role": db_user.role}


@router.put("/users/{user_id}")
async def update_user_role(user_id: UUID, role_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role_data.get("role", user.role)
    db.commit()
    return {"id": str(user.id), "role": user.role}


@router.get("/roles")
async def list_roles():
    return [
        {"name": "host", "permissions": ["podcast:crud", "episode:crud", "research:crud", "script:crud", "translation:crud"]},
        {"name": "researcher", "permissions": ["podcast:r", "episode:r", "research:crud", "script:r"]},
        {"name": "translator", "permissions": ["podcast:r", "episode:r", "script:r", "translation:crud"]},
        {"name": "reader", "permissions": ["podcast:r_published", "episode:r_published", "script:r_published", "translation:r_published"]},
        {"name": "admin", "permissions": ["*"]},
    ]
