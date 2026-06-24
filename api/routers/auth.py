from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from api.config import settings
from api.database import get_db
from api.models.user import User

router = APIRouter()


@router.post("/register")
async def register(user_data: dict, db: Session = Depends(get_db)):
    """Register a new user (public endpoint)."""
    existing = db.query(User).filter(User.email == user_data["email"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

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


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email, "name": current_user.name, "role": current_user.role}
