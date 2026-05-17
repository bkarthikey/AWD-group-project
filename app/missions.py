"""Colony directive missions: pool of 100 harvest targets with score rewards (server-side)."""
from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional

from .colony_service import get_resource_rate, get_upgrade_levels, refresh_colony_score
from .extensions import db
from .models import Colony, Event


def _build_mission_pool() -> List[Dict[str, Any]]:
    """Exactly 100 missions across oxygen / water / minerals with scaling targets and rewards."""
    pool: List[Dict[str, Any]] = []
    mid = 0
    for resource in ("oxygen", "water", "minerals"):
        for tier in range(1, 36):
            mid += 1
            if mid > 100:
                return pool
            target = int(45 + (tier ** 1.82) * 20 + (hash(resource) % 7) * 8)
            reward = max(5, int(8 + tier * 2.1 + (tier ** 1.12)))
            # Soft income floor so new colonies still get viable early directives.
            min_rate = 0.04 + tier * 0.11
            pool.append(
                {
                    "id": mid,
                    "resource": resource,
                    "target": target,
                    "reward": reward,
                    "min_rate": round(min_rate, 2),
                }
            )
    return pool


MISSION_POOL: List[Dict[str, Any]] = _build_mission_pool()


def _load_state(colony: Colony) -> Dict[str, Any]:
    raw = getattr(colony, "missions_json", None) or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"active": [], "done": []}


def _save_state(colony: Colony, state: Dict[str, Any]) -> None:
    colony.missions_json = json.dumps(state)


def harvesting_power(colony: Colony, resource: str) -> float:
    """Rough expected harvest intensity for `resource` (passive + click proxy)."""
    upgrades = get_upgrade_levels(colony)
    rps = upgrades.get(resource, 0) * get_resource_rate(resource, upgrades.get(resource, 0))
    click = upgrades.get("click", 0)
    click_proxy = 1.0 + click * 0.42
    # Cross-type spillover: other extractors slightly raise general activity.
    spill = 0.0
    for r in ("oxygen", "water", "minerals"):
        if r == resource:
            continue
        spill += upgrades.get(r, 0) * get_resource_rate(r, upgrades.get(r, 0)) * 0.06
    return max(0.12, rps + click_proxy * 0.55 + spill)


def _mission_eligible(
    template: Dict[str, Any],
    colony: Colony,
    active_ids: set,
    done: set,
) -> bool:
    if template["id"] in done or template["id"] in active_ids:
        return False
    power = harvesting_power(colony, template["resource"])
    if power < max(0.08, template["min_rate"] * 0.72):
        return False
    est_seconds = template["target"] / power
    if est_seconds < 35:
        return False
    if est_seconds > 9000:
        return False
    return True


def _pick_next_template(colony: Colony, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    active_ids = {m["id"] for m in state.get("active", [])}
    done = set(state.get("done", []))
    candidates = [m for m in MISSION_POOL if _mission_eligible(m, colony, active_ids, done)]
    if not candidates:
        # Relax min_rate slightly so new players still get something.
        active_ids = {m["id"] for m in state.get("active", [])}
        done = set(state.get("done", []))
        for m in MISSION_POOL:
            if m["id"] in done or m["id"] in active_ids:
                continue
            power = harvesting_power(colony, m["resource"])
            est_seconds = m["target"] / max(power, 0.08)
            if 25 <= est_seconds <= 12000:
                candidates.append(m)
    if not candidates:
        return None
    return random.choice(candidates)


def ensure_active_missions(colony: Colony, slots: int = 3) -> None:
    state = _load_state(colony)
    active: List[Dict[str, Any]] = [dict(m) for m in state.get("active", [])]
    changed = False
    while len(active) < slots:
        tpl = _pick_next_template(colony, {"active": active, "done": state.get("done", [])})
        if tpl is None:
            break
        active.append(
            {
                "id": tpl["id"],
                "resource": tpl["resource"],
                "target": tpl["target"],
                "reward": tpl["reward"],
                "progress": 0,
            }
        )
        changed = True
    if changed:
        state["active"] = active
        _save_state(colony, state)


def process_mission_resource_gain(colony: Colony, resource: str, amount: int) -> List[str]:
    """Apply harvest amount toward active missions; grant score_bonus and refill slots on completion."""
    if amount <= 0:
        return []
    state = _load_state(colony)
    active_in = state.get("active", [])
    done = list(state.get("done", []))
    messages: List[str] = []
    new_active: List[Dict[str, Any]] = []

    for m in active_in:
        m = dict(m)
        if m.get("resource") != resource:
            new_active.append(m)
            continue
        prog = int(m.get("progress", 0)) + int(amount)
        target = int(m["target"])
        if prog >= target:
            colony.score_bonus += int(m["reward"])
            mid = int(m["id"])
            if mid not in done:
                done.append(mid)
            res_label = resource.title()
            messages.append(f"Directive complete: harvested {target:,} {res_label}. +{int(m['reward'])} score.")
            db.session.add(
                Event(
                    colony=colony,
                    message=f"Directive complete: +{int(m['reward'])} colony score ({res_label} haul).",
                )
            )
        else:
            m["progress"] = prog
            new_active.append(m)

    state["active"] = new_active
    state["done"] = done[-400:]  # cap growth
    _save_state(colony, state)
    refresh_colony_score(colony)
    ensure_active_missions(colony)
    return messages


def missions_for_api(colony: Colony) -> List[Dict[str, Any]]:
    """Serialize active missions for the dashboard (includes display strings)."""
    state = _load_state(colony)
    out: List[Dict[str, Any]] = []
    labels = {"oxygen": "Oxygen", "water": "Water", "minerals": "Minerals"}
    for m in state.get("active", []):
        res = m["resource"]
        target = int(m["target"])
        progress = min(int(m.get("progress", 0)), target)
        out.append(
            {
                "id": int(m["id"]),
                "resource": res,
                "target": target,
                "progress": progress,
                "reward": int(m["reward"]),
                "title": f"Harvest {target:,} {labels.get(res, res)}",
                "subtitle": f"Earn +{int(m['reward'])} score when complete",
            }
        )
    return out
