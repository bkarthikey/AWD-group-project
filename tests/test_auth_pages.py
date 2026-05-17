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


def test_signup_shows_error_when_passwords_do_not_match():
    app, client = make_client()

    response = client.post(
        "/signup",
        data={
            "username": "Mismatch",
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "different123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Passwords must match." in response.data

    with app.app_context():
        assert User.query.filter_by(email="mismatch@example.com").first() is None


def test_auth_pages_render_password_visibility_controls():
    _, client = make_client()

    signup_response = client.get("/signup")
    login_response = client.get("/login")

    assert signup_response.data.count(b"data-password-toggle") == 2
    assert login_response.data.count(b"data-password-toggle") == 1


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


def test_forgot_password_does_not_change_password_when_email_cannot_send():
    app, client = make_client()
    with app.app_context():
        user = User(username="NoMail", email="nomail@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/forgot-password",
        data={"email": "nomail@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Your password has not been changed." in response.data

    with app.app_context():
        user = User.query.filter_by(email="nomail@example.com").first()
        assert user.check_password("password123")


def test_forgot_password_changes_password_after_successful_email(monkeypatch):
    app, client = make_client()
    with app.app_context():
        user = User(username="MailOk", email="mailok@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    monkeypatch.setattr("app.routes.generate_temporary_password", lambda: "TempPass123")
    monkeypatch.setattr("app.routes.send_temporary_password_email", lambda user, password: True)

    response = client.post(
        "/forgot-password",
        data={"email": "mailok@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A temporary password has been sent to your email." in response.data

    with app.app_context():
        user = User.query.filter_by(email="mailok@example.com").first()
        assert not user.check_password("password123")
        assert user.check_password("TempPass123")


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
