from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.office import Office
from app.models.user import User
from app.schemas.auth import LoginRequest, OfficeRegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: OfficeRegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == payload.owner_email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")

    office = Office(name=payload.office_name)
    db.add(office)
    db.flush()

    owner = User(
        office_id=office.id,
        email=payload.owner_email,
        hashed_password=hash_password(payload.owner_password),
        role="owner",
    )
    db.add(owner)
    db.commit()

    token = create_access_token(office_id=str(office.id), user_id=str(owner.id), role=owner.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya şifre hatalı")

    token = create_access_token(office_id=str(user.office_id), user_id=str(user.id), role=user.role)
    return TokenResponse(access_token=token)
