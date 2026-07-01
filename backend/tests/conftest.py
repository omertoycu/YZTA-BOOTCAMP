import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://portfoyai:portfoyai@localhost:5432/portfoyai_test",
)

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
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.execute(text("TRUNCATE offices, users, listings, leads CASCADE"))
    session.commit()
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)
