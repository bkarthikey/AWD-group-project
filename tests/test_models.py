from app import create_app
from app.extensions import db
from app.models import Colony, User
from config import TestConfig


def test_password_is_hashed():
    user = User(username="Nova", email="nova@example.com")
    user.set_password("password123")

    assert user.password_hash != "password123"
    assert user.check_password("password123")
    assert not user.check_password("wrong-password")


def test_user_can_have_colony():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        user = User(username="Kai", email="kai@example.com")
        user.set_password("password123")
        colony = Colony(user=user)
        db.session.add_all([user, colony])
        db.session.commit()

        saved = User.query.filter_by(username="Kai").first()

        assert saved.colony is not None
        assert saved.colony.oxygen == 120
