from pathlib import Path

from flask import Blueprint, current_app, send_from_directory


main_bp = Blueprint("main", __name__)


def project_root():
    return Path(current_app.root_path).parent


@main_bp.get("/")
def index():
    return send_from_directory(project_root(), "index.html")


@main_bp.get("/dashboard")
def dashboard():
    return send_from_directory(project_root(), "dashboard.html")


@main_bp.get("/upgrades")
def upgrades():
    return send_from_directory(project_root(), "upgrades.html")


@main_bp.get("/leaderboard")
def leaderboard_page():
    return send_from_directory(project_root(), "leaderboard.html")
