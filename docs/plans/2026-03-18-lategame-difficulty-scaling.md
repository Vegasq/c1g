# Late-Game Difficulty Scaling

After the wave-scaling rebalance, playtesting shows enemies become trivial again past wave ~20. Player DPS grows multiplicatively (4 weapons x damage x fire rate) while enemy HP scales linearly (+12%/wave). By wave 30 the player takes zero damage; by wave 50 enemies are deleted on spawn. This plan tightens both sides: slow player power growth and accelerate enemy scaling in late waves.

## Overview

- Files involved: game.py, test_game.py
- Related patterns: Enemy.__init__ (wave scaling), get_scaled_amount(), apply_upgrade(), spawn logic in run(), WAVE_COMPOSITION
- Dependencies: 2026-03-18-rebalance-enemy-wave-scaling (completed)

## Root Cause Analysis

Player DPS at wave 50 (~level 51, 4 weapons):
- Damage per weapon: ~45-50 (scaling +1/+2/+3 per level applied to ALL weapons)
- Fire rate: floor of 5 frames = 12 shots/sec per weapon
- Shotgun: 5 pellets per shot, piercing: multi-hit, explosive: AOE
- Estimated total DPS: 3000+

Enemy HP at wave 50:
- Basic: int(3 * (1 + 0.12*49)) = 20 HP
- Elite: int(15 * 6.88) = 103 HP
- Speed capped at 1.6x base since wave 31
- Contact damage: only 7 (increases every 8 waves)

Result: enemies die in <1 frame, never reaching the player.

## Implementation Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Reduce damage upgrade scaling

Slow player damage growth so late-game DPS doesn't explode.

**Files:**
- Modify: `game.py`

Current get_scaled_amount for damage:
- Level 1-9: +1 per pick
- Level 10-19: +2 per pick
- Level 20+: +3 per pick

New values:
- Level 1-9: +1 per pick (unchanged)
- Level 10-19: +1 per pick (was +2)
- Level 20+: +2 per pick (was +3)

This roughly halves late-game damage accumulation.

- [x] In get_scaled_amount(), change damage scaling: level >= 20 returns base_amount + 1 (was +2), level >= 10 returns base_amount (was +1)
- [x] Update test_get_scaled_amount_damage or equivalent tests to expect new values
- [x] Run tests - must pass before task 2

## Task 2: Compound enemy HP scaling after wave 20

Add exponential multiplier on top of existing linear scaling for late waves. Early game (waves 1-20) unchanged.

**Files:**
- Modify: `game.py`

New HP formula:
```
linear = 1 + 0.12 * (wave - 1)
compound = 1.06 ** max(0, wave - 20)
hp = max(base_hp, int(base_hp * linear * compound))
```

Expected HP at key waves (basic, base=3):
| Wave | Linear only | With compound | Elite (base=15) |
|------|-------------|---------------|-----------------|
| 10   | 6           | 6             | 31              |
| 20   | 10          | 10            | 49              |
| 30   | 17          | 30            | 152             |
| 40   | 24          | 77            | 384             |
| 50   | 20          | 119           | 593             |

- [x] In Enemy.__init__, multiply HP by `1.06 ** max(0, wave - 20)` after existing linear scaling
- [x] Update TestEnemyWaveScaling tests: add test_hp_compound_scaling_after_wave_20 verifying wave 30 and wave 50 values
- [x] Verify test_hp_scales_with_wave (wave 10) still passes unchanged since compound kicks in at wave 21
- [x] Run tests - must pass before task 3

## Task 3: Raise enemy speed cap from 1.6x to 2.0x

Let enemies actually close distance at high waves. Runner at 2.0x = 4.4 speed. Currently speed maxes out at wave 31; with 2.0x cap it maxes at wave 51.

**Files:**
- Modify: `game.py`

Change: `min(1.6, 1 + 0.02 * (wave - 1))` to `min(2.0, 1 + 0.02 * (wave - 1))`

- [x] In Enemy.__init__, change speed cap from 1.6 to 2.0
- [x] Update test_speed_capped to expect 2.0x cap instead of 1.6x (runner at wave 60: 2.2 * 2.0 = 4.4)
- [x] Add test_speed_at_wave_40 verifying intermediate speed (basic: 1.4 * 1.78 = 2.492)
- [x] Run tests - must pass before task 4

## Task 4: Increase contact damage frequency

Change from +1 every 8 waves to +1 every 5 waves so getting hit actually hurts.

**Files:**
- Modify: `game.py`

Change: `1 + (wave - 1) // 8` to `1 + (wave - 1) // 5`

| Wave | Old damage | New damage |
|------|-----------|------------|
| 1    | 1         | 1          |
| 6    | 1         | 2          |
| 10   | 2         | 2          |
| 16   | 2         | 4          |
| 20   | 3         | 4          |
| 25   | 4         | 5          |
| 30   | 4         | 6          |
| 50   | 7         | 10         |

- [x] In Enemy.__init__, change contact_damage divisor from 8 to 5
- [x] Update test_contact_damage_per_wave to expect new values: 1/2/4/5 at waves 1/6/16/25
- [x] Run tests - must pass before task 5

## Task 5: Scale MAX_ENEMIES with wave number

Allow more enemies on screen at high waves to maintain pressure. Current flat cap of 140 lets the player clear everything easily.

**Files:**
- Modify: `game.py`

Change MAX_ENEMIES from a constant to wave-dependent: `min(200, 140 + wave * 2)`

This means:
- Wave 1-10: 142-160 (barely noticeable)
- Wave 20: 180
- Wave 30+: 200 (cap)

- [x] In spawn logic, replace `MAX_ENEMIES` constant check with `min(200, 140 + wave * 2)` or extract a helper function
- [x] Add test_max_enemies_scales_with_wave verifying the formula at wave 1, 20, and 30+
- [x] Run tests - must pass before task 6

## Task 6: Update existing tests, add integration-style balance test

**Files:**
- Modify: `test_game.py`

- [x] Fix any tests broken by the above changes
- [x] Add test_lategame_enemy_survives_base_damage: create a wave-50 basic enemy, assert HP > 100 (ensures compound scaling works)
- [x] Add test_damage_upgrade_diminishing: verify get_scaled_amount returns +1 at level 10, +2 at level 20 (new values)
- [x] Run full test suite: `python -m pytest test_game.py -x -q`

## Expected Balance Curve (after all changes)

| Wave | Basic HP | Elite HP | Speed mult | Contact dmg | Max enemies |
|------|----------|----------|------------|-------------|-------------|
| 1    | 3        | 15       | 1.0x       | 1           | 142         |
| 10   | 6        | 31       | 1.18x      | 2           | 160         |
| 20   | 10       | 49       | 1.38x      | 4           | 180         |
| 30   | 30       | 152      | 1.58x      | 6           | 200         |
| 40   | 77       | 384      | 1.78x      | 8           | 200         |
| 50   | 119      | 593      | 1.98x      | 10          | 200         |

Player damage per weapon at level 50 (estimated, with reduced scaling): ~25-30 instead of ~50.
Combined with 3-6x enemy HP at wave 30-50, enemies should survive multiple hits and reach the player regularly.

## Validation

- [ ] Manual test: play through wave 30+, verify enemies survive multiple hits (requires human playtesting)
- [ ] Manual test: verify player takes damage consistently in waves 20+ (requires human playtesting)
- [x] Run full test suite: `python -m pytest test_game.py -x -q`
- [x] Verify test coverage for new scaling logic

## Cleanup

- [ ] Move this plan to `docs/plans/completed/`
