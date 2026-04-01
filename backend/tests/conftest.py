"""Test fixtures."""
import os
import sys
import tempfile
import pytest

# Set test env vars before importing app
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GITHUB_CLIENT_ID"] = "test_client_id"
os.environ["GITHUB_CLIENT_SECRET"] = "test_client_secret"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_demo"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_demo"
os.environ["FRONTEND_URL"] = "http://localhost:3000"

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db, get_db_path
from app.seed import seed_data
from app.auth import create_token


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Create a fresh test database for each test."""
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path
    # Patch the module-level DB_PATH
    import app.database as db_module
    db_module.DB_PATH = db_path
    init_db()
    seed_data()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Token for the pro test user."""
    return create_token("user_pro_001", "alice-dev")


@pytest.fixture
def free_auth_token():
    """Token for the free test user."""
    return create_token("user_free_002", "bob-builder")


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def free_auth_headers(free_auth_token):
    return {"Authorization": f"Bearer {free_auth_token}"}
