import os
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from .colony_service import apply_passive_income, get_ranked_public_colonies, get_upgrade_levels
from .extensions import db
from .forms import (
    CommentForm,
    DiscussionPostForm,
    LoginForm,
    RegisterForm,
    RewardExchangeForm,
    ThanksMessageForm,
)
from .models import Colony, Comment, DiscussionPost, RewardExchange, User

main_bp = Blueprint("main", __name__)


def ensure_colony(user):
    if user.colony:
        return user.colony

    colony = Colony(user=user)
    db.session.add(colony)
    db.session.commit()
    return colony


def save_discussion_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    safe_name = secure_filename(file_storage.filename)
    _, extension = os.path.splitext(safe_name)
    stored_name = f"{uuid4().hex}{extension.lower()}"
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name))
    return stored_name


def delete_discussion_image(image_filename):
    if not image_filename:
        return

    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_filename)
    if os.path.exists(image_path):
        os.remove(image_path)


@main_bp.get("/")
def index():
    return render_template("index.html")


@main_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("That username or email is already registered.", "error")
            return render_template("signup.html", form=form)

        user = User(username=username, email=email)
        user.set_password(form.password.data)
        colony = Colony(user=user)
        db.session.add_all([user, colony])
        db.session.commit()
        login_user(user)
        flash("Colony account created.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("signup.html", form=form)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Logged in.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html", form=form)


@main_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("main.index"))


@main_bp.get("/dashboard")
@login_required
def dashboard():
    colony = ensure_colony(current_user)
    apply_passive_income(colony)
    db.session.commit()
    return render_template("dashboard.html", colony=colony)


@main_bp.get("/upgrades")
@login_required
def upgrades():
    colony = ensure_colony(current_user)
    apply_passive_income(colony)
    db.session.commit()
    return render_template("upgrades.html", colony=colony)


@main_bp.route("/discussion", methods=["GET", "POST"])
def discussion():
    post_form = DiscussionPostForm(prefix="post")
    comment_form = CommentForm(prefix="comment")
    exchange_form = RewardExchangeForm(prefix="exchange")
    thanks_form = ThanksMessageForm(prefix="thanks")

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to join the discussion board.", "error")
            return redirect(url_for("main.login"))

        if request.form.get("form_name") == "create_post" and post_form.validate_on_submit():
            post = DiscussionPost(
                user=current_user,
                title=post_form.title.data.strip(),
                content=post_form.content.data.strip(),
                image_filename=save_discussion_image(post_form.image.data),
            )
            db.session.add(post)
            attached_offers = []
            for resource_type, amount in {
                "oxygen": post_form.offer_oxygen.data or 0,
                "water": post_form.offer_water.data or 0,
                "minerals": post_form.offer_minerals.data or 0,
            }.items():
                if amount > 0:
                    attached_offers.append(
                        RewardExchange(
                            sender=current_user,
                            resource_type=resource_type,
                            amount=amount,
                            exchange_type="offer",
                            status="open",
                        )
                    )
            db.session.add_all(attached_offers)
            db.session.commit()
            if attached_offers:
                flash("Discussion post and resource offers created.", "success")
            else:
                flash("Discussion post created.", "success")
            return redirect(url_for("main.discussion"))

        if request.form.get("form_name") == "add_comment" and comment_form.validate_on_submit():
            post = db.session.get(DiscussionPost, int(comment_form.post_id.data))
            if not post:
                flash("Discussion post not found.", "error")
                return redirect(url_for("main.discussion"))

            comment = Comment(
                post=post,
                user=current_user,
                content=comment_form.content.data.strip(),
            )
            db.session.add(comment)
            db.session.commit()
            flash("Comment added.", "success")
            return redirect(url_for("main.discussion"))

        if request.form.get("form_name") == "delete_post":
            post_id = request.form.get("post_id", type=int)
            post = db.session.get(DiscussionPost, post_id)

            if not post:
                flash("Discussion post not found.", "error")
                return redirect(url_for("main.discussion"))

            if post.user_id != current_user.id:
                flash("You can only delete your own discussion posts.", "error")
                return redirect(url_for("main.discussion"))

            image_filename = post.image_filename
            db.session.delete(post)
            db.session.commit()
            delete_discussion_image(image_filename)
            flash("Discussion post deleted.", "success")
            return redirect(url_for("main.discussion"))

        if request.form.get("form_name") == "create_exchange" and exchange_form.validate_on_submit():
            receiver_username = (exchange_form.receiver_username.data or "").strip()
            receiver = None
            exchange_type = exchange_form.exchange_type.data

            if exchange_type == "request" and receiver_username:
                flash("Requests are open to any commander and cannot name a receiver.", "error")
                return redirect(url_for("main.discussion"))

            if exchange_type == "offer" and receiver_username:
                receiver = User.query.filter_by(username=receiver_username).first()
                if not receiver:
                    flash("Receiver username not found.", "error")
                    return redirect(url_for("main.discussion"))

            exchange = RewardExchange(
                sender=current_user,
                receiver=receiver,
                resource_type=exchange_form.resource_type.data,
                amount=exchange_form.amount.data,
                exchange_type=exchange_type,
                status="open",
            )
            db.session.add(exchange)
            db.session.commit()
            flash("Reward exchange created.", "success")
            return redirect(url_for("main.discussion"))

        if request.form.get("form_name") == "accept_exchange":
            exchange_id = request.form.get("exchange_id", type=int)
            exchange = db.session.get(RewardExchange, exchange_id)

            if not exchange or exchange.status != "open":
                flash("That reward exchange is no longer available.", "error")
                return redirect(url_for("main.discussion"))

            if exchange.sender_id == current_user.id:
                flash("You cannot accept your own reward exchange.", "error")
                return redirect(url_for("main.discussion"))

            if exchange.exchange_type == "offer" and exchange.receiver_id and exchange.receiver_id != current_user.id:
                flash("This reward exchange is reserved for another commander.", "error")
                return redirect(url_for("main.discussion"))

            requester_colony = ensure_colony(exchange.sender)
            fulfiller_colony = ensure_colony(current_user)
            apply_passive_income(requester_colony)
            apply_passive_income(fulfiller_colony)
            db.session.flush()

            if exchange.exchange_type == "offer":
                source_colony = requester_colony
                destination_colony = fulfiller_colony
                insufficient_message = "Sender no longer has enough resources for this exchange."
            else:
                source_colony = fulfiller_colony
                destination_colony = requester_colony
                insufficient_message = "You do not have enough resources to fulfill this request."

            source_balance = getattr(source_colony, exchange.resource_type)
            if source_balance < exchange.amount:
                db.session.rollback()
                flash(insufficient_message, "error")
                return redirect(url_for("main.discussion"))

            setattr(source_colony, exchange.resource_type, source_balance - exchange.amount)
            setattr(destination_colony, exchange.resource_type, getattr(destination_colony, exchange.resource_type) + exchange.amount)
            exchange.receiver = current_user
            exchange.status = "completed"
            db.session.commit()
            if exchange.exchange_type == "offer":
                flash("Reward exchange completed.", "success")
            else:
                flash("Resource request fulfilled.", "success")
            return redirect(url_for("main.discussion"))

        if request.form.get("form_name") == "send_thanks" and thanks_form.validate_on_submit():
            exchange = db.session.get(RewardExchange, int(thanks_form.exchange_id.data))

            if not exchange or exchange.exchange_type != "request" or exchange.status != "completed":
                flash("That fulfilled request is not available for thanks.", "error")
                return redirect(url_for("main.discussion"))

            if exchange.sender_id != current_user.id:
                flash("Only the requester can send thanks for this exchange.", "error")
                return redirect(url_for("main.discussion"))

            if exchange.receiver_id is None:
                flash("This request has not been fulfilled yet.", "error")
                return redirect(url_for("main.discussion"))

            exchange.thanks_message = thanks_form.message.data.strip()
            db.session.commit()
            flash("Thanks message sent.", "success")
            return redirect(url_for("main.discussion"))

        flash("Please check the discussion form and try again.", "error")

    posts = (
        DiscussionPost.query
        .join(DiscussionPost.user)
        .order_by(DiscussionPost.created_at.desc())
        .all()
    )

    exchange_offers = (
        RewardExchange.query
        .order_by(RewardExchange.created_at.desc())
        .limit(10)
        .all()
    )

    fulfilled_requests = []
    if current_user.is_authenticated:
        fulfilled_requests = (
            RewardExchange.query
            .filter_by(
                sender_id=current_user.id,
                exchange_type="request",
                status="completed",
            )
            .order_by(RewardExchange.created_at.desc())
            .all()
        )

    return render_template(
        "discussion.html",
        posts=posts,
        exchange_offers=exchange_offers,
        post_form=post_form,
        comment_form=comment_form,
        exchange_form=exchange_form,
        thanks_form=thanks_form,
        fulfilled_requests=fulfilled_requests,
    )


@main_bp.get("/leaderboard")
def leaderboard_page():
    colonies = get_ranked_public_colonies()
    return render_template("leaderboard.html", colonies=colonies)


@main_bp.get("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not user.is_public:
        return render_template("profile-private.html", profile_user=user)

    colony = ensure_colony(user)
    apply_passive_income(colony)
    db.session.commit()
    upgrade_levels = get_upgrade_levels(colony)
    profile_stats = {
        "total_extractors": sum(upgrade_levels.values()),
        "oxygen_extractors": upgrade_levels["oxygen"],
        "water_extractors": upgrade_levels["water"],
        "mineral_extractors": upgrade_levels["minerals"],
    }
    return render_template("profile.html", profile_user=user, colony=colony, profile_stats=profile_stats)


@main_bp.get("/profile")
@login_required
def my_profile():
    return redirect(url_for("main.profile", username=current_user.username))
@main_bp.post("/profile/privacy")
@login_required
def update_profile_privacy():
    current_user.is_public = "is_public" in request.form
    db.session.commit()

    if current_user.is_public:
        flash("Your colony profile is now public.", "success")
    else:
        flash("Your colony profile is now private.", "success")

    return redirect(url_for("main.my_profile"))
