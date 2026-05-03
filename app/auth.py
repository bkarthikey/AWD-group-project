from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import Colony, User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or len(password) < 8:
        return jsonify({"error": "Username, email, and an 8 character password are required."}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "That username or email is already registered."}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    colony = Colony(user=user)
    db.session.add_all([user, colony])
    db.session.commit()
    login_user(user)

    return jsonify({"message": "Account created.", "user": {"id": user.id, "username": user.username}}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    login_user(user, remember=bool(data.get("remember")))
    return jsonify({"message": "Logged in.", "user": {"id": user.id, "username": user.username}})


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out."})


@auth_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False})

    return jsonify({
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_public": current_user.is_public,
        },
    })
