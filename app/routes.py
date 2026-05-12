from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .forms import LoginForm, RegisterForm
from .models import Colony, User

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


@main_bp.get("/discussion")
def discussion():
    posts = [
        {
            "username": "NovaPrime",
            "colony_name": "Aurora Outpost",
            "timestamp": "Today 09:40",
            "title": "Early oxygen strategy",
            "content": "I rush oxygen extractors first, then use minerals for drills once the colony can survive without constant clicking.",
            "image": True,
            "reward": {"oxygen": 80, "water": 20, "minerals": 0},
            "comments": [
                {"username": "LunaForge", "text": "This works well if you keep water above 50 before upgrading.", "timestamp": "Today 09:55"},
                {"username": "MarsMiner", "text": "I pair this with mineral drills for faster score growth.", "timestamp": "Today 10:02"},
            ],
        },
        {
            "username": "AstroKai",
            "colony_name": "Crater Nine",
            "timestamp": "Yesterday 21:18",
            "title": "Trading spare water",
            "content": "My colony has extra water production. I can exchange water for minerals with anyone building drills.",
            "image": False,
            "reward": {"oxygen": 0, "water": 120, "minerals": 0},
            "comments": [
                {"username": "NovaPrime", "text": "Happy to trade minerals once my next drill comes online.", "timestamp": "Yesterday 21:31"},
            ],
        },
    ]

    exchange_offers = [
        {"sender": "NovaPrime", "receiver": "Any commander", "resource": "oxygen", "amount": 80, "status": "Open"},
        {"sender": "AstroKai", "receiver": "MarsMiner", "resource": "water", "amount": 120, "status": "Pending"},
        {"sender": "LunaForge", "receiver": "Any commander", "resource": "minerals", "amount": 45, "status": "Open"},
    ]

    return render_template("discussion.html", posts=posts, exchange_offers=exchange_offers)


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
