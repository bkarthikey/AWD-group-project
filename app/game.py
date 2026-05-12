from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from .extensions import db
from .models import Colony, Event, Upgrade, User


game_bp = Blueprint("game", __name__, url_prefix="/api")

UPGRADES = {
    "oxygen": {"cost_resource": "minerals", "base_cost": 50, "rate": 1.2},
    "water": {"cost_resource": "oxygen", "base_cost": 40, "rate": 1.0},
    "minerals": {"cost_resource": "water", "base_cost": 60, "rate": 1.4},
}


def get_upgrade_cost(upgrade_type, level):
    return int(UPGRADES[upgrade_type]["base_cost"] * (1.55 ** level))


def get_or_create_upgrade(colony, upgrade_type):
    upgrade = Upgrade.query.filter_by(colony=colony, upgrade_type=upgrade_type).first()
    if upgrade:
        return upgrade

    upgrade = Upgrade(colony=colony, upgrade_type=upgrade_type, level=0)
    db.session.add(upgrade)
    return upgrade


def colony_payload(colony):
    upgrades = {upgrade.upgrade_type: upgrade.level for upgrade in colony.upgrades}
    for upgrade_type in UPGRADES:
        upgrades.setdefault(upgrade_type, 0)

    return {
        "resources": colony.resource_dict(),
        "upgrades": upgrades,
        "rates": {
            upgrade_type: round(upgrades[upgrade_type] * config["rate"], 1)
            for upgrade_type, config in UPGRADES.items()
        },
    }


@game_bp.get("/colony-state")
@login_required
def colony_state():
    return jsonify(colony_payload(current_user.colony))


@game_bp.post("/collect")
@login_required
def collect():
    data = request.get_json(silent=True) or {}
    resource = data.get("resource", "minerals")
    amount = int(data.get("amount", 1))

    if resource not in ("oxygen", "water", "minerals") or amount < 1 or amount > 50:
        return jsonify({"error": "Invalid collection request."}), 400

    colony = current_user.colony
    setattr(colony, resource, getattr(colony, resource) + amount)
    colony.total_collected += amount
    colony.score += amount * 2
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
    upgrade = get_or_create_upgrade(colony, upgrade_type)
    config = UPGRADES[upgrade_type]
    cost = get_upgrade_cost(upgrade_type, upgrade.level)
    available = getattr(colony, config["cost_resource"])

    if available < cost:
        return jsonify({"error": "Not enough resources.", "cost": cost}), 400

    setattr(colony, config["cost_resource"], available - cost)
    upgrade.level += 1
    colony.score += cost * 3
    db.session.add(Event(colony=colony, message=f"{upgrade_type.title()} extractor upgraded to level {upgrade.level}."))
    db.session.commit()

    return jsonify(colony_payload(colony))


@game_bp.get("/leaderboard")
def leaderboard():
    colonies = (
        Colony.query.join(Colony.user)
        .filter_by(is_public=True)
        .order_by(Colony.score.desc())
        .limit(10)
        .all()
    )

    return jsonify([
        {
            "rank": index + 1,
            "username": colony.user.username,
            "colony_name": colony.name,
            "score": colony.score,
            "oxygen": colony.oxygen,
            "water": colony.water,
            "minerals": colony.minerals,
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
            "colony_name": user.colony.name if user.colony else "New Colony",
            "is_public": user.is_public,
            "profile_url": f"/profile/{user.username}",
        }
        for user in users
    ])
