import os

os.environ["SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-1234567890"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["APP_ENV"] = "test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["PASSWORD_RESET_EXPOSE_TOKEN"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.rate_limit import login_limiter, password_reset_limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    login_limiter.clear()
    password_reset_limiter.clear()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def csrf_headers(client):
    def headers():
        token = client.cookies.get("kc_csrf")
        return {"X-CSRF-Token": token} if token else {}

    return headers


@pytest.fixture
def make_admin(session):
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.repositories.users import UserRepository

    def factory(email="admin@example.com", password="AdminPass1"):
        user = UserRepository(session).create(
            email=email,
            password_hash=hash_password(password),
            full_name="Test Administrator",
            phone=None,
            role=UserRole.ADMIN.value,
        )
        session.commit()
        return user, password

    return factory
