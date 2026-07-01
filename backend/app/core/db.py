from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
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
