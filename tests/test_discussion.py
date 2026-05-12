from app import create_app
from app.extensions import db
from app.models import Comment, DiscussionPost, RewardExchange, User
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


def test_logged_in_user_can_create_discussion_post():
    app = create_app(TestConfig)
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
            "post-image_filename": "oxygen-base.png",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Best oxygen start" in response.data

    with app.app_context():
        saved_post = DiscussionPost.query.filter_by(title="Best oxygen start").first()
        assert saved_post is not None
        assert saved_post.image_filename == "oxygen-base.png"


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
