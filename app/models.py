from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    colony = db.relationship("Colony", back_populates="user", uselist=False, cascade="all, delete-orphan")
    discussion_posts = db.relationship("DiscussionPost", back_populates="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    sent_reward_exchanges = db.relationship(
        "RewardExchange",
        back_populates="sender",
        cascade="all, delete-orphan",
        foreign_keys="RewardExchange.sender_id",
    )
    received_reward_exchanges = db.relationship(
        "RewardExchange",
        back_populates="receiver",
        foreign_keys="RewardExchange.receiver_id",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Colony(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    name = db.Column(db.String(100), default="New Dawn Outpost", nullable=False)
    oxygen = db.Column(db.Integer, default=120, nullable=False)
    water = db.Column(db.Integer, default=90, nullable=False)
    minerals = db.Column(db.Integer, default=180, nullable=False)
    score = db.Column(db.Integer, default=0, nullable=False)
    total_collected = db.Column(db.Integer, default=0, nullable=False)
    best_combo = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="colony")
    upgrades = db.relationship("Upgrade", back_populates="colony", cascade="all, delete-orphan")
    events = db.relationship("Event", back_populates="colony", cascade="all, delete-orphan")

    def resource_dict(self):
        return {
            "oxygen": self.oxygen,
            "water": self.water,
            "minerals": self.minerals,
            "score": self.score,
            "total_collected": self.total_collected,
            "best_combo": self.best_combo,
        }


class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    colony_id = db.Column(db.Integer, db.ForeignKey("colony.id"), nullable=False)
    upgrade_type = db.Column(db.String(40), nullable=False)
    level = db.Column(db.Integer, default=0, nullable=False)

    colony = db.relationship("Colony", back_populates="upgrades")

    __table_args__ = (db.UniqueConstraint("colony_id", "upgrade_type", name="unique_colony_upgrade"),)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    colony_id = db.Column(db.Integer, db.ForeignKey("colony.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    colony = db.relationship("Colony", back_populates="events")


class DiscussionPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="discussion_posts")
    comments = db.relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("discussion_post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = db.relationship("DiscussionPost", back_populates="comments")
    user = db.relationship("User", back_populates="comments")


class RewardExchange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    resource_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="open", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    sender = db.relationship("User", back_populates="sent_reward_exchanges", foreign_keys=[sender_id])
    receiver = db.relationship("User", back_populates="received_reward_exchanges", foreign_keys=[receiver_id])
