from app import create_app
from app.extensions import db
from app.models import User
from config import TestConfig


def make_client():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
    return app, client


def test_signup_creates_user_and_colony():
    app, client = make_client()

    response = client.post(
        "/signup",
        data={
            "username": "Orion",
            "email": "orion@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="orion@example.com").first()
        assert user is not None
        assert user.colony is not None


def test_login_allows_dashboard_access():
    app, client = make_client()
    with app.app_context():
        user = User(username="Vega", email="vega@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={"email": "vega@example.com", "password": "password123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Colony Status" in response.data


def test_dashboard_requires_login():
    app, client = make_client()

    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
