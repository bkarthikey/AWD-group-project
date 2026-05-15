from app import create_app
from app.extensions import db
from app.models import Colony, Upgrade, User
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


def test_public_profile_shows_real_colony_stats():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(username="Atlas", email="atlas@example.com")
        user.set_password("password123")
        colony = Colony(
            user=user,
            name="Atlas Prime",
            oxygen=410,
            water=275,
            minerals=920,
            score=1500,
            total_collected=820,
            best_combo=14,
        )
        db.session.add_all([
            user,
            colony,
            Upgrade(colony=colony, upgrade_type="oxygen", level=2),
            Upgrade(colony=colony, upgrade_type="water", level=3),
            Upgrade(colony=colony, upgrade_type="minerals", level=4),
        ])
        db.session.commit()

    response = client.get("/profile/Atlas")

    assert response.status_code == 200
    assert b"Atlas Prime" in response.data
    assert b"1,500" in response.data
    assert b"820" in response.data
    assert b"x14" in response.data
    assert b"410" in response.data
    assert b"275" in response.data
    assert b"920" in response.data
    assert b"9" in response.data
