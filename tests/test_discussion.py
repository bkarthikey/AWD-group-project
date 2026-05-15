from io import BytesIO

from app import create_app
from app.extensions import db
from app.models import Colony, Comment, DiscussionPost, RewardExchange, User
from config import TestConfig


def test_discussion_page_loads():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()

    response = client.get("/discussion")

    assert response.status_code == 200
    assert b"Discussion Board" in response.data
    assert b"Reward exchange" in response.data


def test_discussion_models_store_post_comment_and_exchange():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        sender = User(username="Nova", email="nova@example.com")
        receiver = User(username="Kai", email="kai@example.com")
        sender.set_password("password123")
        receiver.set_password("password123")
        db.session.add_all([sender, receiver])
        db.session.commit()

        post = DiscussionPost(user=sender, title="Oxygen plan", content="Upgrade oxygen first.")
        db.session.add(post)
        db.session.commit()

        comment = Comment(post=post, user=receiver, content="Good strategy.")
        exchange = RewardExchange(
            sender=sender,
            receiver=receiver,
            resource_type="oxygen",
            amount=25,
            status="open",
        )
        db.session.add_all([comment, exchange])
        db.session.commit()

        saved_post = DiscussionPost.query.first()
        saved_exchange = RewardExchange.query.first()

        assert saved_post.user.username == "Nova"
        assert saved_post.comments[0].content == "Good strategy."
        assert saved_exchange.receiver.username == "Kai"


def test_logged_in_user_can_create_discussion_post(tmp_path):
    app = create_app(TestConfig)
    app.config["UPLOAD_FOLDER"] = tmp_path
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(username="Orion", email="orion@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    client.post("/login", data={"email": "orion@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "create_post",
            "post-title": "Best oxygen start",
            "post-content": "Build oxygen extractor before mineral drill.",
            "post-image": (BytesIO(b"fake image bytes"), "oxygen-base.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Best oxygen start" in response.data

    with app.app_context():
        saved_post = DiscussionPost.query.filter_by(title="Best oxygen start").first()
        assert saved_post is not None
        assert saved_post.image_filename.endswith(".png")
        assert (tmp_path / saved_post.image_filename).exists()


def test_discussion_post_rejects_non_image_upload(tmp_path):
    app = create_app(TestConfig)
    app.config["UPLOAD_FOLDER"] = tmp_path
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(username="Kepler", email="kepler@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    client.post("/login", data={"email": "kepler@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "create_post",
            "post-title": "My upload test",
            "post-content": "Trying to upload a text file.",
            "post-image": (BytesIO(b"plain text"), "notes.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please check the discussion form and try again." in response.data

    with app.app_context():
        assert DiscussionPost.query.count() == 0


def test_logged_in_user_can_comment_on_discussion_post():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(username="Lyra", email="lyra@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        post = DiscussionPost(user=user, title="Mineral plan", content="Drills after oxygen.")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    client.post("/login", data={"email": "lyra@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "add_comment",
            "comment-post_id": str(post_id),
            "comment-content": "This helped my colony survive longer.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"This helped my colony survive longer." in response.data

    with app.app_context():
        saved_comment = Comment.query.filter_by(content="This helped my colony survive longer.").first()
        assert saved_comment is not None
        assert saved_comment.post_id == post_id


def test_logged_in_user_can_create_reward_exchange_offer():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Vega", email="vega@example.com")
        receiver = User(username="Atlas", email="atlas@example.com")
        sender.set_password("password123")
        receiver.set_password("password123")
        db.session.add_all([sender, receiver])
        db.session.commit()

    client.post("/login", data={"email": "vega@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "create_exchange",
            "exchange-resource_type": "water",
            "exchange-amount": "45",
            "exchange-receiver_username": "Atlas",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"45 water" in response.data
    assert b"to Atlas" in response.data

    with app.app_context():
        saved_exchange = RewardExchange.query.filter_by(resource_type="water").first()
        assert saved_exchange is not None
        assert saved_exchange.amount == 45
        assert saved_exchange.sender.username == "Vega"
        assert saved_exchange.receiver.username == "Atlas"


def test_reward_exchange_requires_existing_receiver_when_named():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Sol", email="sol@example.com")
        sender.set_password("password123")
        db.session.add(sender)
        db.session.commit()

    client.post("/login", data={"email": "sol@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "create_exchange",
            "exchange-resource_type": "oxygen",
            "exchange-amount": "30",
            "exchange-receiver_username": "MissingUser",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Receiver username not found." in response.data

    with app.app_context():
        assert RewardExchange.query.count() == 0


def test_user_can_accept_open_reward_exchange_and_receive_resources():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Nova", email="nova@example.com")
        receiver = User(username="Kai", email="kai@example.com")
        sender.set_password("password123")
        receiver.set_password("password123")
        sender_colony = Colony(user=sender, oxygen=90)
        receiver_colony = Colony(user=receiver, oxygen=20)
        exchange = RewardExchange(sender=sender, resource_type="oxygen", amount=30, status="open")
        db.session.add_all([sender, receiver, sender_colony, receiver_colony, exchange])
        db.session.commit()
        exchange_id = exchange.id

    client.post("/login", data={"email": "kai@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "accept_exchange",
            "exchange_id": str(exchange_id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Reward exchange completed." in response.data

    with app.app_context():
        saved_exchange = RewardExchange.query.first()
        sender = User.query.filter_by(username="Nova").first()
        receiver = User.query.filter_by(username="Kai").first()
        assert saved_exchange.status == "completed"
        assert saved_exchange.receiver.username == "Kai"
        assert sender.colony.oxygen == 60
        assert receiver.colony.oxygen == 50


def test_user_cannot_accept_own_reward_exchange():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Vega", email="vega@example.com")
        sender.set_password("password123")
        colony = Colony(user=sender, minerals=80)
        exchange = RewardExchange(sender=sender, resource_type="minerals", amount=25, status="open")
        db.session.add_all([sender, colony, exchange])
        db.session.commit()
        exchange_id = exchange.id

    client.post("/login", data={"email": "vega@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "accept_exchange",
            "exchange_id": str(exchange_id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You cannot accept your own reward exchange." in response.data

    with app.app_context():
        saved_exchange = RewardExchange.query.first()
        assert saved_exchange.status == "open"
        assert saved_exchange.receiver is None


def test_reward_exchange_rejects_wrong_reserved_receiver():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Sol", email="sol@example.com")
        reserved_receiver = User(username="Lyra", email="lyra@example.com")
        other_user = User(username="Orion", email="orion@example.com")
        for user in (sender, reserved_receiver, other_user):
            user.set_password("password123")
        db.session.add_all([
            sender,
            reserved_receiver,
            other_user,
            Colony(user=sender, water=70),
            Colony(user=reserved_receiver),
            Colony(user=other_user),
        ])
        db.session.flush()
        exchange = RewardExchange(
            sender=sender,
            receiver=reserved_receiver,
            resource_type="water",
            amount=20,
            status="open",
        )
        db.session.add(exchange)
        db.session.commit()
        exchange_id = exchange.id

    client.post("/login", data={"email": "orion@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "accept_exchange",
            "exchange_id": str(exchange_id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"This reward exchange is reserved for another commander." in response.data

    with app.app_context():
        saved_exchange = RewardExchange.query.first()
        assert saved_exchange.status == "open"
        assert saved_exchange.receiver.username == "Lyra"


def test_reward_exchange_rejects_transfer_when_sender_lacks_resources():
    app = create_app(TestConfig)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        sender = User(username="Atlas", email="atlas@example.com")
        receiver = User(username="Mira", email="mira@example.com")
        sender.set_password("password123")
        receiver.set_password("password123")
        sender_colony = Colony(user=sender, water=10)
        receiver_colony = Colony(user=receiver, water=15)
        exchange = RewardExchange(sender=sender, resource_type="water", amount=30, status="open")
        db.session.add_all([sender, receiver, sender_colony, receiver_colony, exchange])
        db.session.commit()
        exchange_id = exchange.id

    client.post("/login", data={"email": "mira@example.com", "password": "password123"})
    response = client.post(
        "/discussion",
        data={
            "form_name": "accept_exchange",
            "exchange_id": str(exchange_id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Sender no longer has enough resources for this exchange." in response.data

    with app.app_context():
        saved_exchange = RewardExchange.query.first()
        sender = User.query.filter_by(username="Atlas").first()
        receiver = User.query.filter_by(username="Mira").first()
        assert saved_exchange.status == "open"
        assert saved_exchange.receiver is None
        assert sender.colony.water == 10
        assert receiver.colony.water == 15
