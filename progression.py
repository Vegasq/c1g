"""Roguelite meta-progression system for Squad Survivors.

Provides:
- 8 upgrade categories with infinite scaling formulas
- Player profile persistence (profile.json)
- Per-run upgrade generation and application
- Cross-run upgrade saving on death
"""

import json
import math
import os
import random

# ---------------------------------------------------------------------------
# Profile persistence
# ---------------------------------------------------------------------------
PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json")

_UPGRADE_KEYS = [
    "max_hp", "move_speed",
    "weapon_normal", "weapon_shotgun", "weapon_piercing", "weapon_explosive",
    "ally_spawn", "heal_amount",
]

LOCKABLE_WEAPONS = {"weapon_shotgun", "weapon_piercing", "weapon_explosive", "weapon_mine"}

# Weapon type string for each weapon category
_WEAPON_TYPE_MAP = {
    "weapon_normal": "normal",
    "weapon_shotgun": "shotgun",
    "weapon_piercing": "piercing",
    "weapon_explosive": "explosive",
    "weapon_mine": "mine",
}


def default_profile():
    """Return a fresh player profile with no upgrades."""
    return {
        "version": 1,
        "upgrades": {k: 0 for k in _UPGRADE_KEYS},
        "total_runs": 0,
        "best_wave": 0,
    }


def load_profile():
    """Load player profile from disk. Returns default if missing or corrupt."""
    try:
        with open(PROFILE_FILE, "r") as f:
            data = json.load(f)
        # Validate structure
        if not isinstance(data.get("upgrades"), dict):
            return default_profile()
        profile = default_profile()
        for k in _UPGRADE_KEYS:
            val = data["upgrades"].get(k, 0)
            if isinstance(val, (int, float)) and val >= 0:
                profile["upgrades"][k] = int(val)
        profile["total_runs"] = int(data.get("total_runs", 0))
        profile["best_wave"] = int(data.get("best_wave", 0))
        return profile
    except (json.JSONDecodeError, IOError, OSError, KeyError, TypeError, ValueError):
        return default_profile()


def save_profile(profile):
    """Save player profile to disk (atomic write)."""
    tmp = PROFILE_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(profile, f, indent=2)
        os.replace(tmp, PROFILE_FILE)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Scaling formulas
# ---------------------------------------------------------------------------

# Base weapon stats (must match game.py default_weapon_stats)
_WEAPON_DEFAULTS = {
    "damage": 1,
    "fire_rate": 25,
    "bullet_speed": 8,
    "range": 90,
}


def compute_max_hp(level):
    """Compute max HP at given upgrade level. Linear scaling."""
    return 5 + level


def compute_move_speed(level):
    """Compute movement speed at given upgrade level. Logarithmic diminishing returns."""
    if level <= 0:
        return 3.5
    return 3.5 + 0.15 * math.log(1 + level * 1.5)


def compute_ally_spawn_chance(level):
    """Compute ally spawn probability at given upgrade level."""
    if level <= 0:
        return 0.10
    return 0.10 + 0.03 * math.log(1 + level)


def compute_heal_amount(level):
    """Compute health pickup restore amount at given upgrade level."""
    return 1 + level


def compute_mine_stats(level):
    """Compute mine weapon stats at given upgrade level.

    Returns None if level <= 0 (weapon locked).
    Level 1 = base stats. Level 2+ = faster deploy and more damage.
    """
    if level <= 0:
        return None
    base = {
        "damage": 2,
        "fire_rate": 180,  # 3 seconds between deploys at 60fps
        "bullet_speed": 0,
        "range": 0,
    }
    if level == 1:
        return base
    base["damage"] += int(level * 0.5)
    base["fire_rate"] = max(60, base["fire_rate"] - int(15 * level))
    return base


def compute_weapon_stats(level):
    """Compute weapon stats dict at given upgrade level.

    Returns None if level <= 0 (weapon locked).
    Level 1 = base stats. Level 2+ = scaled bonuses.
    """
    if level <= 0:
        return None
    base = dict(_WEAPON_DEFAULTS)
    if level == 1:
        return base
    # Level 2+: apply bonuses
    base["damage"] += int(level * 0.8)
    base["fire_rate"] = max(5, base["fire_rate"] - int(1.5 * math.log(1 + level)))
    base["bullet_speed"] += int(0.8 * level)
    base["range"] += int(5 * level)
    return base


# ---------------------------------------------------------------------------
# Upgrade category definitions
# ---------------------------------------------------------------------------

UPGRADE_CATEGORIES = {
    "max_hp": {
        "name": "Max HP",
        "description": "Increase maximum health",
        "compute": compute_max_hp,
        "lockable": False,
        "format_value": lambda lvl: f"HP: {compute_max_hp(lvl)}",
    },
    "move_speed": {
        "name": "Move Speed",
        "description": "Increase movement speed",
        "compute": compute_move_speed,
        "lockable": False,
        "format_value": lambda lvl: f"Speed: {compute_move_speed(lvl):.2f}",
    },
    "weapon_normal": {
        "name": "Normal Weapon",
        "description": "Upgrade basic weapon stats",
        "compute": compute_weapon_stats,
        "lockable": False,
        "format_value": lambda lvl: _format_weapon(lvl),
    },
    "weapon_shotgun": {
        "name": "Shotgun",
        "description": "Spread weapon",
        "compute": compute_weapon_stats,
        "lockable": True,
        "format_value": lambda lvl: _format_weapon(lvl),
    },
    "weapon_piercing": {
        "name": "Piercing",
        "description": "Piercing rounds",
        "compute": compute_weapon_stats,
        "lockable": True,
        "format_value": lambda lvl: _format_weapon(lvl),
    },
    "weapon_explosive": {
        "name": "Explosive",
        "description": "Explosive rounds",
        "compute": compute_weapon_stats,
        "lockable": True,
        "format_value": lambda lvl: _format_weapon(lvl),
    },
    "weapon_mine": {
        "name": "Land Mine",
        "description": "Drop mines that explode\non enemy contact",
        "compute": compute_mine_stats,
        "lockable": True,
        "format_value": lambda lvl: _format_mine(lvl),
    },
    "ally_spawn": {
        "name": "Ally Spawn Rate",
        "description": "Increase chance of \nally spawning on kill",
        "compute": compute_ally_spawn_chance,
        "lockable": False,
        "format_value": lambda lvl: f"Chance: {compute_ally_spawn_chance(lvl):.0%}",
    },
    "heal_amount": {
        "name": "Health Restore",
        "description": "Increase health pickup healing",
        "compute": compute_heal_amount,
        "lockable": False,
        "format_value": lambda lvl: f"Heal: {compute_heal_amount(lvl)} HP",
    },
}


def _format_weapon(level):
    """Format weapon stats for display."""
    stats = compute_weapon_stats(level)
    if stats is None:
        return "Locked"
    return f"Damage:{stats['damage']} \nRate:{stats['fire_rate']} \nSpeed:{stats['bullet_speed']}"


def _format_mine(level):
    """Format mine stats for display."""
    stats = compute_mine_stats(level)
    if stats is None:
        return "Locked"
    return f"Damage:{stats['damage']} \nDeploy:{stats['fire_rate']}f"


# ---------------------------------------------------------------------------
# Per-run upgrade generation and application
# ---------------------------------------------------------------------------

def generate_upgrade_options(run_upgrade_levels):
    """Generate 3 random upgrade options from the 8 categories.

    Args:
        run_upgrade_levels: dict mapping category keys to current run levels

    Returns:
        list of 3 option dicts with keys: category, name, current_level, is_unlock
    """
    keys = list(UPGRADE_CATEGORIES.keys())
    chosen = random.sample(keys, min(3, len(keys)))
    options = []
    for key in chosen:
        cat = UPGRADE_CATEGORIES[key]
        current = run_upgrade_levels.get(key, 0)
        is_unlock = cat["lockable"] and current == 0
        options.append({
            "category": key,
            "name": cat["name"],
            "current_level": current,
            "is_unlock": is_unlock,
        })
    return options


def apply_upgrade(option, run_upgrade_levels, weapon_inventory, player, game_vars):
    """Apply a chosen upgrade to the game state.

    Args:
        option: dict from generate_upgrade_options
        run_upgrade_levels: dict to update
        weapon_inventory: list of weapon dicts
        player: Unit instance
        game_vars: dict with ally_spawn_chance, heal_restore_amount, player_speed
    """
    key = option["category"]
    old_level = run_upgrade_levels.get(key, 0)
    new_level = old_level + 1
    run_upgrade_levels[key] = new_level

    if key == "max_hp":
        old_hp = compute_max_hp(old_level)
        new_hp = compute_max_hp(new_level)
        delta = new_hp - old_hp
        player.max_hp += delta
        player.hp = min(player.hp + delta, player.max_hp)

    elif key == "move_speed":
        player.player_speed = compute_move_speed(new_level)
        game_vars["player_speed"] = player.player_speed

    elif key.startswith("weapon_"):
        weapon_type = _WEAPON_TYPE_MAP[key]
        compute_fn = compute_mine_stats if key == "weapon_mine" else compute_weapon_stats
        new_stats = compute_fn(new_level)
        if new_stats is None:
            return  # shouldn't happen since new_level >= 1

        if old_level == 0:
            # Unlock: add new weapon to inventory
            weapon = dict(new_stats)
            weapon["weapon_type"] = weapon_type
            weapon["cooldown"] = 0
            weapon_inventory.append(weapon)
        else:
            # Upgrade: find and update existing weapon
            for ws in weapon_inventory:
                if ws.get("weapon_type") == weapon_type:
                    ws["damage"] = new_stats["damage"]
                    ws["fire_rate"] = new_stats["fire_rate"]
                    ws["bullet_speed"] = new_stats.get("bullet_speed", ws.get("bullet_speed", 0))
                    ws["range"] = new_stats.get("range", ws.get("range", 0))
                    break

    elif key == "ally_spawn":
        game_vars["ally_spawn_chance"] = compute_ally_spawn_chance(new_level)

    elif key == "heal_amount":
        game_vars["heal_restore_amount"] = compute_heal_amount(new_level)


def apply_profile_to_game(profile, player, weapon_inventory):
    """Apply all profile upgrades to game state at run start.

    Args:
        profile: loaded profile dict
        player: Unit instance (just created)
        weapon_inventory: list with one normal weapon

    Returns:
        game_vars dict with: ally_spawn_chance, heal_restore_amount, player_speed
    """
    levels = profile["upgrades"]
    game_vars = {
        "ally_spawn_chance": 0.10,
        "heal_restore_amount": 1,
        "player_speed": 3.5,
    }

    # Max HP
    hp_level = levels.get("max_hp", 0)
    if hp_level > 0:
        player.max_hp = compute_max_hp(hp_level)
        player.hp = player.max_hp

    # Move speed
    speed_level = levels.get("move_speed", 0)
    if speed_level > 0:
        player.player_speed = compute_move_speed(speed_level)
        game_vars["player_speed"] = player.player_speed

    # Normal weapon upgrades
    normal_level = levels.get("weapon_normal", 0)
    if normal_level > 0:
        stats = compute_weapon_stats(normal_level)
        if stats and weapon_inventory:
            ws = weapon_inventory[0]
            ws["damage"] = stats["damage"]
            ws["fire_rate"] = stats["fire_rate"]
            ws["bullet_speed"] = stats["bullet_speed"]
            ws["range"] = stats["range"]

    # Locked weapons — unlock if profile level >= 1
    for wkey in ("weapon_shotgun", "weapon_piercing", "weapon_explosive"):
        wlevel = levels.get(wkey, 0)
        if wlevel >= 1:
            stats = compute_weapon_stats(wlevel)
            if stats:
                weapon = dict(stats)
                weapon["weapon_type"] = _WEAPON_TYPE_MAP[wkey]
                weapon["cooldown"] = 0
                weapon_inventory.append(weapon)

    # Ally spawn rate
    ally_level = levels.get("ally_spawn", 0)
    if ally_level > 0:
        game_vars["ally_spawn_chance"] = compute_ally_spawn_chance(ally_level)

    # Health restore
    heal_level = levels.get("heal_amount", 0)
    if heal_level > 0:
        game_vars["heal_restore_amount"] = compute_heal_amount(heal_level)

    return game_vars


# ---------------------------------------------------------------------------
# Death — compute earned upgrades and save one to profile
# ---------------------------------------------------------------------------

def compute_run_earned_upgrades(profile_start_levels, run_levels):
    """Compute list of individual upgrade events earned during this run.

    Each entry represents one level-up in one category.
    Only includes upgrades that exceed the current profile level,
    so saving one can never downgrade the player's profile.

    Returns:
        list of dicts: {"category": key, "name": display_name, "from_level": N, "to_level": N+1}
    """
    earned = []
    for key in _UPGRADE_KEYS:
        start = profile_start_levels.get(key, 0)
        end = run_levels.get(key, 0)
        cat = UPGRADE_CATEGORIES[key]
        for lvl in range(start, end):
            earned.append({
                "category": key,
                "name": cat["name"],
                "from_level": lvl,
                "to_level": lvl + 1,
            })
    return earned


def select_saved_upgrade(earned_upgrades, profile):
    """Randomly select one upgrade event to save to profile.

    Only considers upgrades whose to_level exceeds the current profile
    level for that category, ensuring we never downgrade progress.

    Returns:
        (index, upgrade_event) tuple, or (None, None) if nothing qualifies
    """
    if not earned_upgrades:
        return None, None
    # Filter to only upgrades that would actually raise the profile level
    profile_levels = profile.get("upgrades", {})
    eligible = []
    for i, upg in enumerate(earned_upgrades):
        current_profile_level = profile_levels.get(upg["category"], 0)
        if upg["to_level"] > current_profile_level:
            eligible.append((i, upg))
    if not eligible:
        return None, None
    idx, upg = random.choice(eligible)
    return idx, upg


def save_run_upgrade_to_profile(profile, upgrade_event, wave=0):
    """Save a single upgrade event to the player profile.

    Only saves if the upgrade's target level exceeds the current profile
    level, preventing any accidental downgrade of player progress.
    """
    key = upgrade_event["category"]
    current = profile["upgrades"].get(key, 0)
    target = upgrade_event.get("to_level", current + 1)
    if target > current:
        profile["upgrades"][key] = target
    profile["total_runs"] = profile.get("total_runs", 0) + 1
    if wave > profile.get("best_wave", 0):
        profile["best_wave"] = wave
    save_profile(profile)
