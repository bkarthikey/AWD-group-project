from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .forms import CommentForm, DiscussionPostForm, LoginForm, RegisterForm, RewardExchangeForm
from .models import Colony, Comment, DiscussionPost, RewardExchange, User

main_bp = Blueprint("main", __name__)


def ensure_colony(user):
    if user.colony:
        return user.colony

    colony = Colony(user=user)
    db.session.add(colony)
    db.session.commit()
    return colony


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
    return render_template("dashboard.html", colony=ensure_colony(current_user))


@main_bp.get("/upgrades")
@login_required
def upgrades():
    return render_template("upgrades.html", colony=ensure_colony(current_user))


@main_bp.route("/discussion", methods=["GET", "POST"])
def discussion():
    post_form = DiscussionPostForm(prefix="post")
    comment_form = CommentForm(prefix="comment")
    exchange_form = RewardExchangeForm(prefix="exchange")

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to join the discussion board.", "error")
            return redirect(url_for("main.login"))

        if request.form.get("form_name") == "create_post" and post_form.validate_on_submit():
            image_filename = (post_form.image_filename.data or "").strip() or None
            post = DiscussionPost(
                user=current_user,
                title=post_form.title.data.strip(),
                content=post_form.content.data.strip(),
                image_filename=image_filename,
            )
            db.session.add(post)
            db.session.commit()
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

        if request.form.get("form_name") == "create_exchange" and exchange_form.validate_on_submit():
            receiver_username = (exchange_form.receiver_username.data or "").strip()
            receiver = None

            if receiver_username:
                receiver = User.query.filter_by(username=receiver_username).first()
                if not receiver:
                    flash("Receiver username not found.", "error")
                    return redirect(url_for("main.discussion"))

            exchange = RewardExchange(
                sender=current_user,
                receiver=receiver,
                resource_type=exchange_form.resource_type.data,
                amount=exchange_form.amount.data,
                status="open",
            )
            db.session.add(exchange)
            db.session.commit()
            flash("Reward exchange offer created.", "success")
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

    return render_template(
        "discussion.html",
        posts=posts,
        exchange_offers=exchange_offers,
        post_form=post_form,
        comment_form=comment_form,
        exchange_form=exchange_form,
    )


@main_bp.get("/leaderboard")
def leaderboard_page():
    colonies = (
        Colony.query.join(Colony.user)
        .filter_by(is_public=True)
        .order_by(Colony.score.desc())
        .limit(10)
        .all()
    )
    return render_template("leaderboard.html", colonies=colonies)


@main_bp.get("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not user.is_public:
        return render_template("profile-private.html", profile_user=user)

    return render_template("profile.html", profile_user=user, colony=ensure_colony(user))


@main_bp.get("/profile")
@login_required
def my_profile():
    return redirect(url_for("main.profile", username=current_user.username))
