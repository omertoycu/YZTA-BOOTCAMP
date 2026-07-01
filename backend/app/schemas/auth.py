from pydantic import BaseModel, EmailStr


class OfficeRegisterRequest(BaseModel):
    office_name: str
    owner_email: EmailStr
    owner_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
