# Weapon Persistence and Enemy Rebalancing

## Overview

Two main changes: (1) Weapons accumulate during a run instead of replacing - player fires all collected weapon types simultaneously, and (2) enemy spawn counts reduced to 60-80% with buffed stats.

- **Files involved**: `game.py`
- **Related patterns**: existing `weapon_stats` dict, `ENEMY_TYPES` dict, spawn logic in `run()`
- **Dependencies**: none

## Implementation Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Refactor weapon system from single weapon to multi-weapon inventory

**Files:**
- Modify: `game.py`

- [x] Change `weapon_stats` from a single dict to a list of weapon dicts. Player starts with one "normal" weapon entry.
- [x] Modify `Unit.shoot_at()` to iterate over all weapons in inventory, firing each weapon type on its own cooldown cycle.
- [x] Update `apply_upgrade()`: stat upgrades (damage, fire rate, bullet speed, range) apply to ALL weapons in inventory. Weapon type milestone adds a NEW weapon entry with default stats plus any global bonuses earned so far.
- [x] Update `generate_upgrade_options()`: at milestones, only offer weapon types not already in inventory. If all types collected, offer a stat upgrade instead.
- [x] Update `draw_upgrade_panel()` / HUD to show current weapon inventory (list of collected weapon types).
- [x] Write tests for multi-weapon firing, upgrade application to all weapons, and milestone weapon addition.
- [x] Run project test suite - must pass before task 2.

## Task 2: Rebalance enemy spawning - reduce count, buff stats

**Files:**
- Modify: `game.py`

- [x] Reduce `MAX_ENEMIES` from 200 to 140 (70% of current).
- [x] Reduce spawn count per event: change formula from `wave + wave // 2` to `wave + wave // 4` (roughly 60-70% of current at higher waves).
- [x] Increase initial `spawn_interval` from 90 to 110 (slower early ramp).
- [x] Buff `ENEMY_TYPES` stats: increase HP by ~50% across all types (basic: 3, runner: 2, brute: 9, shielded: 6, splitter: 4, mini: 2, elite: 15). Increase speed slightly for basic and brute (+0.2 each).
- [x] Increase XP values proportionally to compensate for fewer but tougher enemies (roughly +50%: basic: 2, runner: 2, brute: 5, shielded: 6, splitter: 3, mini: 1, elite: 12).
- [x] Write tests for updated enemy stats and spawn rate calculations.
- [x] Run project test suite - must pass before task 3.

## Task 3: Integration testing and balance verification

**Files:**
- Modify: `game.py` (if adjustments needed)

- [ ] Manual test: start game, verify normal weapon fires, reach first milestone, pick shotgun, verify BOTH normal and shotgun fire simultaneously.
- [ ] Manual test: continue playing, pick third weapon type, verify all three fire.
- [ ] Manual test: verify enemy count feels noticeably lower but enemies are tougher.
- [ ] Manual test: verify stat upgrades apply to all weapons in inventory.
- [ ] Run full test suite.
- [ ] Run linter.

## Cleanup

- [ ] Move this plan to `docs/plans/completed/`
