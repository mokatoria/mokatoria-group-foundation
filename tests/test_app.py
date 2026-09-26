import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import Config
from extensions import db
from models import Donation


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # simplifies posting forms in tests
    STRIPE_SECRET_KEY = ""     # forces DEMO_MODE for these tests


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Give Back" in response.data


def test_donate_page_loads(client):
    response = client.get("/donate")
    assert response.status_code == 200
    assert b"Make a donation" in response.data


def test_successful_donation_demo_mode(client, app):
    response = client.post(
        "/donate",
        data={"name": "Jane Doe", "email": "jane@example.com", "amount": "25.00", "message": "Keep it up!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Thank you, Jane Doe" in response.data

    with app.app_context():
        donation = Donation.query.filter_by(email="jane@example.com").first()
        assert donation is not None
        assert donation.status == "completed"
        assert donation.amount == 25.00


def test_donation_rejects_invalid_amount(client):
    response = client.post(
        "/donate",
        data={"name": "Jane Doe", "email": "jane@example.com", "amount": "-5", "message": ""},
    )
    assert response.status_code == 200  # re-renders form with errors
    assert b"between $1 and $100,000" in response.data


def test_donation_rejects_invalid_email(client):
    response = client.post(
        "/donate",
        data={"name": "Jane Doe", "email": "not-an-email", "amount": "10", "message": ""},
    )
    assert response.status_code == 200
    assert b"Invalid email" in response.data or b"invalid" in response.data.lower()


def test_home_page_reflects_completed_total(client):
    client.post(
        "/donate",
        data={"name": "A", "email": "a@example.com", "amount": "10", "message": ""},
    )
    client.post(
        "/donate",
        data={"name": "B", "email": "b@example.com", "amount": "15", "message": ""},
    )
    response = client.get("/")
    assert b"25.00" in response.data
