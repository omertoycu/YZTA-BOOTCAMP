import os
import tempfile

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault(
    "MIGRATIONS_DATABASE_URL",
    "postgresql+psycopg2://portfoyai:portfoyai@localhost:5432/portfoyai_test",
)
# Uygulama testlerde de kısıtlı app rolüyle bağlanmalı; aksi halde RLS testi
# superuser bypass'ı yüzünden yanlışlıkla "geçer" (bkz. 0002_app_role_least_privilege).
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://portfoyai_app:portfoyai_app@localhost:5432/portfoyai_test",
)
os.environ.setdefault(
    "AUTH_DATABASE_URL",
    "postgresql+psycopg2://portfoyai_auth:portfoyai_auth@localhost:5432/portfoyai_test",
)
# Her test session'ı için ayrı, geçici bir ChromaDB dizini — dev index'iyle
# karışmasın ve testler arası veri birikmesin.
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="portfoyai_chroma_test_"))

from app.main import app  # noqa: E402  (env var yukarıda set edildikten sonra import edilmeli)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture()
def db_session():
    """RLS'i baypas eden, tam yetkili bağlantı — doğrudan DB kurulumu/temizliği için."""
    engine = create_engine(os.environ["MIGRATIONS_DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.execute(text("TRUNCATE offices, users, listings, leads CASCADE"))
    session.commit()
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)
