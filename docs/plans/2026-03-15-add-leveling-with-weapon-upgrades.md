# Add Leveling with Weapon Upgrades

Add XP-based leveling system with weapon stat upgrades and new weapon types at milestone levels. Enemies grant XP on kill, with increasing XP thresholds per level. On level up, the player picks from offered upgrades (damage, fire rate, bullet speed, range). Every 5 levels, a new weapon type is offered (shotgun spread, piercing bullets, explosive rounds).

## Overview

- **Files involved**: `game.py`
- **Related patterns**: single-file pygame game, class-based entities (Bullet, Unit, Enemy)
- **Dependencies**: none

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1 - XP and leveling data model

**Files:**
- Modify: `game.py`

- [x] Add xp, level, xp_thresholds tracking to the player state in run() (e.g. xp=0, level=1, thresholds like 10, 25, 50, 80, 120... scaling)
- [x] Award XP when enemies are killed (1 XP per kill)
- [x] Detect level-up when xp >= threshold, increment level, reset xp counter
- [x] Display level and XP bar in the HUD
- [x] Write tests for XP accumulation, level-up threshold logic
- [x] Run tests - must pass before task 2

## Task 2 - Weapon stats system

**Files:**
- Modify: `game.py`

- [ ] Add weapon stats dict to player state: damage (default 1), fire_rate (default 25 cooldown), bullet_speed (default 8), range (default 90 frames lifetime), weapon_type (default "normal")
- [ ] Make Bullet class use these stats (pass them to constructor) instead of class-level constants
- [ ] Make Unit.shoot_at use player weapon stats for cooldown and range check distance
- [ ] Write tests for weapon stats affecting bullet behavior
- [ ] Run tests - must pass before task 3

## Task 3 - Level-up upgrade selection UI

**Files:**
- Modify: `game.py`

- [ ] Add STATE_LEVEL_UP game state that pauses gameplay
- [ ] On level up, generate 3 random upgrade options: +damage, +fire_rate, +bullet_speed, +range (stat boosts)
- [ ] At milestone levels (5, 10, 15...), replace one option with a new weapon type (shotgun, piercing, explosive)
- [ ] Draw upgrade selection screen showing 3 options, selectable with 1/2/3 keys
- [ ] Apply selected upgrade to player weapon stats
- [ ] Write tests for upgrade generation logic and stat application
- [ ] Run tests - must pass before task 4

## Task 4 - New weapon types implementation

**Files:**
- Modify: `game.py`

- [ ] Shotgun: fires 5 bullets in a spread pattern instead of 1, each with reduced damage
- [ ] Piercing: bullets pass through enemies instead of being destroyed on hit (track hits per bullet)
- [ ] Explosive: bullets deal area damage on hit (damage nearby enemies within blast radius)
- [ ] Weapon type affects bullet creation in shoot_at and collision handling in the main loop
- [ ] Write tests for each weapon type behavior
- [ ] Run tests - must pass before task 5

## Task 5 - Polish and integration

**Files:**
- Modify: `game.py`

- [ ] Show current level and weapon type in HUD
- [ ] Add XP bar below health bar or in HUD area
- [ ] Reset leveling state in reset_game()
- [ ] Display level reached on game over screen
- [ ] Write integration tests for full level-up flow
- [ ] Run full test suite

## Final Verification

- [ ] manual test: kill enemies, gain XP, level up, pick upgrades, reach level 5 for weapon unlock
- [ ] run full test suite
- [ ] verify test coverage meets 80%+

## Wrap-up

- [ ] move this plan to `docs/plans/completed/`
