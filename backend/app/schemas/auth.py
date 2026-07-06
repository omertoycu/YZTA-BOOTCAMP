import re

from pydantic import BaseModel, EmailStr, field_validator

PASSWORD_MIN_LENGTH = 8


def validate_password_strength(password: str) -> str:
    """Şifre politikası: en az 8 karakter, en az bir büyük harf, bir küçük
    harf, bir rakam ve bir özel karakter. Sadece kayıt/şifre değiştirmede
    uygulanır — LoginRequest'e bilerek uygulanmıyor, aksi halde politika
    öncesi oluşturulmuş hesaplar giriş yapamaz hale gelirdi."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Şifre en az {PASSWORD_MIN_LENGTH} karakter olmalı")
    if not re.search(r"[A-ZÇĞİÖŞÜ]", password):
        raise ValueError("Şifre en az bir büyük harf içermeli")
    if not re.search(r"[a-zçğıöşü]", password):
        raise ValueError("Şifre en az bir küçük harf içermeli")
    if not re.search(r"\d", password):
        raise ValueError("Şifre en az bir rakam içermeli")
    if not re.search(r"[^\w\s]", password):
        raise ValueError("Şifre en az bir özel karakter içermeli (örn. ! @ # $ %)")
    return password


class OfficeRegisterRequest(BaseModel):
    office_name: str
    owner_email: EmailStr
    owner_password: str

    @field_validator("owner_password")
    @classmethod
    def _check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
