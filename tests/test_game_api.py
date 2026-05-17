from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models import Colony, Upgrade, User
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


def test_collect_persists_to_sqlite_and_colony_state_matches():
    app, client = create_logged_in_client()

    assert client.post("/api/collect", json={"resource": "oxygen", "amount": 5}).status_code == 200

    with app.app_context():
        colony = Colony.query.first()
        assert colony.oxygen == 55
        assert colony.total_collected == 5

    state = client.get("/api/colony-state")
    assert state.status_code == 200
    data = state.get_json()
    assert data["resources"]["oxygen"] == 55
    assert data["resources"]["total_collected"] == 5
    assert data["upgrades"]["oxygen"] == 0

    with app.app_context():
        db.drop_all()


def test_buy_upgrade_persists_to_sqlite_and_colony_state_matches():
    app, client = create_logged_in_client()

    with app.app_context():
        colony = Colony.query.first()
        colony.minerals = 200
        db.session.commit()

    assert client.post("/api/buy-upgrade", json={"upgrade_type": "oxygen"}).status_code == 200

    with app.app_context():
        colony = Colony.query.first()
        assert colony.minerals == 80
        assert colony.upgrades[0].level == 1

    state = client.get("/api/colony-state")
    assert state.status_code == 200
    data = state.get_json()
    assert data["resources"]["minerals"] == 80
    assert data["upgrades"]["oxygen"] == 1

    with app.app_context():
        db.drop_all()


def test_collect_increases_resource():
    app, client = create_logged_in_client()

    response = client.post("/api/collect", json={"resource": "oxygen", "amount": 5})

    assert response.status_code == 200
    assert response.get_json()["resources"]["oxygen"] == 55

    with app.app_context():
        db.drop_all()


def test_collect_score_is_one_per_twelve_resources_not_combo_scaled():
    app, client = create_logged_in_client()

    response = client.post(
        "/api/collect",
        json={"resource": "oxygen", "amount": 5, "best_combo": 4, "combo": 4, "critical": True},
    )

    assert response.status_code == 200
    assert response.get_json()["resources"]["score"] == 0

    with app.app_context():
        colony = Colony.query.first()
        assert colony.total_collected == 5
        assert colony.score == 0
        db.drop_all()


def test_collect_rejects_invalid_combo():
    app, client = create_logged_in_client()

    response = client.post(
        "/api/collect",
        json={"resource": "oxygen", "amount": 5, "best_combo": 1, "combo": 30, "critical": False},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid collection request."

    with app.app_context():
        db.drop_all()


def test_collect_persists_higher_best_combo():
    app, client = create_logged_in_client()

    response = client.post("/api/collect", json={"resource": "oxygen", "amount": 5, "best_combo": 9})

    assert response.status_code == 200
    assert response.get_json()["resources"]["best_combo"] == 9

    with app.app_context():
        colony = Colony.query.first()
        assert colony.best_combo == 9
        db.drop_all()


def test_collect_does_not_lower_existing_best_combo():
    app, client = create_logged_in_client()
    with app.app_context():
        colony = Colony.query.first()
        colony.best_combo = 12
        db.session.commit()

    response = client.post("/api/collect", json={"resource": "water", "amount": 3, "best_combo": 4})

    assert response.status_code == 200
    assert response.get_json()["resources"]["best_combo"] == 12

    with app.app_context():
        colony = Colony.query.first()
        assert colony.best_combo == 12
        db.drop_all()


def test_collect_rejects_invalid_best_combo():
    app, client = create_logged_in_client()

    response = client.post("/api/collect", json={"resource": "minerals", "amount": 1, "best_combo": 30})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid collection request."

    with app.app_context():
        db.drop_all()


def test_buy_upgrade_spends_resource_and_increases_level():
    app, client = create_logged_in_client()

    with app.app_context():
        colony = Colony.query.first()
        colony.minerals = 200
        db.session.commit()

    response = client.post("/api/buy-upgrade", json={"upgrade_type": "oxygen"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["resources"]["minerals"] == 80
    assert data["upgrades"]["oxygen"] == 1

    with app.app_context():
        db.drop_all()


def test_colony_state_applies_passive_income_from_extractors():
    app, client = create_logged_in_client()

    with app.app_context():
        colony = Colony.query.first()
        colony.updated_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.session.add(Upgrade(colony=colony, upgrade_type="oxygen", level=2))
        db.session.commit()

    response = client.get("/api/colony-state")

    assert response.status_code == 200
    data = response.get_json()
    assert data["resources"]["oxygen"] >= 102
    assert data["resources"]["total_collected"] >= 52
    assert data["resources"]["score"] == 4

    with app.app_context():
        saved_colony = Colony.query.first()
        assert saved_colony.oxygen >= 102
        assert saved_colony.total_collected >= 52
        assert saved_colony.score == 4
        db.drop_all()


def test_leaderboard_refreshes_passive_income_without_changing_score_ranking():
    app, client = create_logged_in_client()

    with app.app_context():
        nova = Colony.query.first()
        nova.score_bonus = 5
        nova.total_collected = 0
        nova.updated_at = datetime.now(timezone.utc)
        challenger = User(username="Atlas", email="atlas@example.com")
        challenger.set_password("password123")
        challenger_colony = Colony(
            user=challenger,
            oxygen=120,
            water=90,
            minerals=180,
            score_bonus=1,
            total_collected=0,
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add_all([challenger, challenger_colony])
        db.session.flush()
        db.session.add(Upgrade(colony=challenger_colony, upgrade_type="minerals", level=1))
        db.session.commit()

    response = client.get("/api/leaderboard")

    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["username"] == "Nova"
    assert data[0]["score"] == 5

    with app.app_context():
        db.drop_all()


def test_user_search_returns_matching_users():
    app, client = create_logged_in_client()
    with app.app_context():
        user = User(username="LunaForge", email="luna@example.com")
        user.set_password("password123")
        colony = Colony(user=user, name="Moon Forge")
        db.session.add_all([user, colony])
        db.session.commit()

    response = client.get("/api/users/search?q=luna")

    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["username"] == "LunaForge"
    assert data[0]["colony_name"] == "Moon Forge"

    with app.app_context():
        db.drop_all()


def test_user_search_hides_private_colony_name():
    app, client = create_logged_in_client()
    with app.app_context():
        user = User(username="HiddenLuna", email="hidden@example.com", is_public=False)
        user.set_password("password123")
        colony = Colony(user=user, name="Secret Base")
        db.session.add_all([user, colony])
        db.session.commit()

    response = client.get("/api/users/search?q=hidden")

    assert response.status_code == 200
    data = response.get_json()
    assert data[0]["username"] == "HiddenLuna"
    assert data[0]["colony_name"] is None
    assert data[0]["is_public"] is False

    with app.app_context():
        db.drop_all()


def test_user_search_short_query_returns_empty_list():
    app, client = create_logged_in_client()

    response = client.get("/api/users/search?q=n")

    assert response.status_code == 200
    assert response.get_json() == []

    with app.app_context():
        db.drop_all()
