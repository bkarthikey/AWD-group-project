from datetime import datetime, timezone

from .extensions import db
from .models import Colony, Upgrade, User


UPGRADES = {
    "oxygen": {"cost_resource": "minerals", "base_cost": 120, "cost_growth": 2.0, "base_rate": 2.0},
    "water": {"cost_resource": "oxygen", "base_cost": 120, "cost_growth": 2.0, "base_rate": 2.0},
    "minerals": {"cost_resource": "water", "base_cost": 120, "cost_growth": 2.0, "base_rate": 2.0},
    "click": {"cost_resource": "mixed", "base_cost": 60, "cost_growth": 2.0, "base_rate": 0},
}


def get_upgrade_cost(upgrade_type, level):
    return int(UPGRADES[upgrade_type]["base_cost"] * (UPGRADES[upgrade_type]["cost_growth"] ** level))


def get_resource_rate(upgrade_type, level):
    if level <= 0:
        return 0
    return UPGRADES[upgrade_type]["base_rate"] + 0.6 * max(0, level - 1)


def get_or_create_upgrade(colony, upgrade_type):
    upgrade = Upgrade.query.filter_by(colony=colony, upgrade_type=upgrade_type).first()
    if upgrade:
        return upgrade

    upgrade = Upgrade(colony=colony, upgrade_type=upgrade_type, level=0)
    db.session.add(upgrade)
    return upgrade


def get_upgrade_levels(colony):
    upgrades = {upgrade.upgrade_type: upgrade.level for upgrade in colony.upgrades}
    for upgrade_type in UPGRADES:
        upgrades.setdefault(upgrade_type, 0)
    return upgrades


def apply_passive_income(colony, now=None):
    now = now or datetime.now(timezone.utc)
    last_update = colony.updated_at
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)

    elapsed_seconds = int((now - last_update).total_seconds())
    if elapsed_seconds <= 0:
        return False

    upgrades = get_upgrade_levels(colony)
    total_earned = 0

    for upgrade_type, config in UPGRADES.items():
        if upgrade_type == "click":
            continue

        rate = get_resource_rate(upgrade_type, upgrades[upgrade_type])
        earned = int(upgrades[upgrade_type] * rate * elapsed_seconds)
        if earned <= 0:
            continue

        setattr(colony, upgrade_type, getattr(colony, upgrade_type) + earned)
        total_earned += earned

    colony.total_collected += total_earned
    colony.updated_at = now
    return total_earned > 0


def colony_payload(colony):
    upgrades = get_upgrade_levels(colony)

    return {
        "resources": colony.resource_dict(),
        "upgrades": upgrades,
        "rates": {
            upgrade_type: round(upgrades[upgrade_type] * get_resource_rate(upgrade_type, upgrades[upgrade_type]), 1)
            for upgrade_type in UPGRADES
        },
    }


def get_ranked_public_colonies(limit=10):
    colonies = Colony.query.join(Colony.user).filter(User.is_public.is_(True)).all()
    for colony in colonies:
        apply_passive_income(colony)

    db.session.commit()
    return sorted(colonies, key=lambda colony: colony.score, reverse=True)[:limit]
