# Rebalance Enemy Wave Scaling

Add wave-based scaling to enemies so the game stays challenging in mid-to-late waves. Currently enemies never scale while player DPS grows without bound, resulting in zero damage taken after wave ~20. Enemies will scale HP, speed, XP, and contact damage based on wave number. Also raises fire_rate floor from 3 to 5 to slow DPS growth.

## Overview

- Files involved: game.py, test_game.py
- Related patterns: ENEMY_TYPES dict, Enemy class, apply_upgrade(), spawn logic in run()
- Dependencies: none

## Implementation Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Add enemy wave scaling in Enemy.__init__

**Files:**
- Modify: `game.py`

- [x] Add `wave=1` parameter to `Enemy.__init__` (line 717)
- [x] HP scaling: `base_hp * (1 + 0.12 * (wave - 1))`, int-rounded, min = base
- [x] Speed scaling: `base_speed * min(1.6, 1 + 0.02 * (wave - 1))`
- [x] XP scaling: `base_xp + wave // 5`
- [x] Contact damage: `1 + (wave - 1) // 8` stored as `self.contact_damage`
- [x] Run tests - must pass before task 2

## Task 2: Pass wave to Enemy construction (2 locations)

**Files:**
- Modify: `game.py`

- [x] Main spawn loop (line ~1863): `Enemy(camera, enemy_type=etype, wave=wave)`
- [x] Mini spawns from splitters (line ~1983): `Enemy(camera, enemy_type="mini", wave=wave)`
- [x] Run tests - must pass before task 3

## Task 3: Use e.contact_damage in player collision

**Files:**
- Modify: `game.py`

- [ ] Change `player.hp -= 1` to `player.hp -= e.contact_damage` (line ~2036)
- [ ] Update `run_stats["damage_taken"]` and `run_stats["wave_damage_taken"]` to add `e.contact_damage` instead of 1
- [ ] Run tests - must pass before task 4

## Task 4: Raise fire_rate floor from 3 to 5

**Files:**
- Modify: `game.py`

- [ ] Change 3 occurrences of `max(3, ...)` in apply_upgrade() to `max(5, ...)` (lines 950, 964, 968)
- [ ] Run tests - must pass before task 5

## Task 5: Update existing tests, add new tests

**Files:**
- Modify: `test_game.py`

- [ ] Update `test_fire_rate_clamped_to_minimum` (line 267) expected value from 3 to 5
- [ ] Add `TestEnemyWaveScaling` class with tests:
  - `test_wave_1_uses_base_stats` - no scaling at wave 1
  - `test_hp_scales_with_wave` - basic at wave 10: int(3 * 2.08) = 6
  - `test_elite_hp_at_wave_20` - int(15 * 3.28) = 49
  - `test_speed_scales_with_wave` - basic at wave 10: 1.4 * 1.18 = 1.652
  - `test_speed_capped` - runner at wave 50: max 2.2 * 1.6 = 3.52
  - `test_contact_damage_per_wave` - 1/2/3/4 at waves 1/9/17/25
  - `test_xp_scales_with_wave` - basic at wave 10: 2 + 10//5 = 4
  - `test_mini_spawns_get_wave_scaling` - verify wave param is used
- [ ] Run full test suite

## Expected Balance Curve

| Wave | Basic HP | Elite HP | Speed mult | Contact dmg | Player context |
|------|----------|----------|------------|-------------|----------------|
| 1    | 3        | 15       | 1.0x       | 1           | Same as today |
| 5    | 4        | 22       | 1.08x      | 1           | Still easy |
| 10   | 6        | 31       | 1.18x      | 2           | Challenging |
| 15   | 8        | 40       | 1.28x      | 2           | Enemies survive multiple hits |
| 20   | 10       | 49       | 1.38x      | 3           | Hits hurt, dodging matters |
| 25   | 14       | 58       | 1.48x      | 4           | Genuinely threatening |
| 30   | 17       | 67       | 1.58x      | 4           | Very hard |

## Validation

- [ ] Manual test: play through wave 15+, verify enemies get noticeably tougher
- [ ] Manual test: verify contact damage increases are felt
- [ ] Run full test suite: `python -m pytest test_game.py -x -q`
- [ ] Verify test coverage meets 80%+

## Cleanup

- [ ] Move this plan to `docs/plans/completed/`
