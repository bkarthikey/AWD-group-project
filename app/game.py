from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .colony_service import (
    UPGRADES,
    apply_passive_income,
    colony_payload,
    get_or_create_upgrade,
    get_ranked_public_colonies,
    get_upgrade_cost,
)
from .extensions import db
from .models import Event, User


game_bp = Blueprint("game", __name__, url_prefix="/api")


@game_bp.get("/colony-state")
@login_required
def colony_state():
    apply_passive_income(current_user.colony)
    db.session.commit()
    return jsonify(colony_payload(current_user.colony))


@game_bp.post("/collect")
@login_required
def collect():
    data = request.get_json(silent=True) or {}
    resource = data.get("resource", "minerals")
    amount = int(data.get("amount", 1))
    best_combo = int(data.get("best_combo", 1))
    combo = int(data.get("combo", 1))
    critical = bool(data.get("critical", False))

    if (
        resource not in ("oxygen", "water", "minerals")
        or amount < 1
        or amount > 50
        or best_combo < 1
        or best_combo > 25
        or combo < 1
        or combo > 25
    ):
        return jsonify({"error": "Invalid collection request."}), 400

    colony = current_user.colony
    apply_passive_income(colony)
    setattr(colony, resource, getattr(colony, resource) + amount)
    colony.total_collected += amount
    colony.score += amount * combo * (4 if critical else 2)
    colony.best_combo = max(colony.best_combo, best_combo)
    db.session.commit()

    return jsonify(colony_payload(colony))


@game_bp.post("/buy-upgrade")
@login_required
def buy_upgrade():
    data = request.get_json(silent=True) or {}
    upgrade_type = data.get("upgrade_type")

    if upgrade_type not in UPGRADES:
        return jsonify({"error": "Unknown upgrade type."}), 400

    colony = current_user.colony
    apply_passive_income(colony)
    upgrade = get_or_create_upgrade(colony, upgrade_type)
    config = UPGRADES[upgrade_type]
    cost = get_upgrade_cost(upgrade_type, upgrade.level)

    if config["cost_resource"] == "mixed":
        per_resource = cost // 3
        if colony.oxygen < per_resource or colony.water < per_resource or colony.minerals < per_resource:
            return jsonify({"error": "Not enough resources." , "cost": cost}), 400
        colony.oxygen -= per_resource
        colony.water -= per_resource
        colony.minerals -= per_resource
    else:
        available = getattr(colony, config["cost_resource"])
        if available < cost:
            return jsonify({"error": "Not enough resources.", "cost": cost}), 400
        setattr(colony, config["cost_resource"], available - cost)

    upgrade.level += 1
    colony.score += cost * 3
    event_label = config["cost_resource"] == "mixed" and "Harvest Enhancer" or f"{upgrade_type.title()} extractor"
    db.session.add(Event(colony=colony, message=f"{event_label} upgraded to level {upgrade.level}."))
    db.session.commit()

    return jsonify(colony_payload(colony))


@game_bp.get("/leaderboard")
def leaderboard():
    colonies = get_ranked_public_colonies()

    return jsonify([
        {
            "rank": index + 1,
            "username": colony.user.username,
            "colony_name": colony.name,
            "score": colony.score,
            "oxygen": colony.oxygen,
            "water": colony.water,
            "minerals": colony.minerals,
            "best_combo": colony.best_combo,
            "total_collected": colony.total_collected, 
        }
        for index, colony in enumerate(colonies)
    ])


@game_bp.get("/users/search")
def search_users():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    users = (
        User.query
        .filter(User.username.ilike(f"%{query}%"))
        .order_by(User.username.asc())
        .limit(8)
        .all()
    )

    return jsonify([
        {
            "username": user.username,
            "colony_name": user.colony.name if user.is_public and user.colony else None,
            "is_public": user.is_public,
            "profile_url": f"/profile/{user.username}",
            "rank": user.colony.score if user.colony else 0,
        }
        for user in users
    ])
