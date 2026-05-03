from app import create_app
from app.extensions import db
from app.models import Colony, User
from config import TestConfig


def create_logged_in_client():
    app = create_app(TestConfig)
    client = app.test_client()

    with app.app_context():
        db.create_all()
        user = User(username="Nova", email="nova@example.com")
        user.set_password("password123")
        colony = Colony(user=user)
        db.session.add_all([user, colony])
        db.session.commit()

    client.post("/auth/login", json={"email": "nova@example.com", "password": "password123"})
    return app, client


def test_collect_increases_resource():
    app, client = create_logged_in_client()

    response = client.post("/api/collect", json={"resource": "oxygen", "amount": 5})

    assert response.status_code == 200
    assert response.get_json()["resources"]["oxygen"] == 125

    with app.app_context():
        db.drop_all()


def test_buy_upgrade_spends_resource_and_increases_level():
    app, client = create_logged_in_client()

    response = client.post("/api/buy-upgrade", json={"upgrade_type": "oxygen"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["resources"]["minerals"] == 130
    assert data["upgrades"]["oxygen"] == 1

    with app.app_context():
        db.drop_all()
