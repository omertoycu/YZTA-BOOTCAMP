from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
# expire_on_commit=False: commit sonrası nesne özniteliklerine erişim yeni bir
# SELECT tetiklemesin. Tetiklerse o SELECT, SET LOCAL ile bağlı tenant context'i
# commit'te sıfırlanmış yeni bir transaction'da çalışır ve RLS satırı gizler.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Sadece auth.py (register/login) kullanmalı — bkz. app/core/config.py: auth_database_url
auth_engine = create_engine(settings.auth_database_url, pool_pre_ping=True)
AuthSessionLocal = sessionmaker(bind=auth_engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Sadece public.py (login'siz ilan vitrini) kullanmalı — bkz. app/core/config.py: public_database_url
public_engine = create_engine(settings.public_database_url, pool_pre_ping=True)
PublicSessionLocal = sessionmaker(bind=public_engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_public_db():
    db = PublicSessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant(db: Session, office_id: str) -> None:
    """Multi-tenant RLS'in çalışması için her request'te çağrılmalı.

    Atlanırsa Postgres policy'leri current_setting'i bulamaz ve
    varsayılan olarak hiçbir satırı döndürmez (sessiz veri kaybı gibi görünür).
    """
    db.execute(text("SET LOCAL app.current_office_id = :office_id"), {"office_id": office_id})
