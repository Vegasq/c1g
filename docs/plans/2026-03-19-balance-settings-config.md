# Balance Settings Config

Extract all hardcoded balance values from game.py into a balance.toml config file with comments. The game reads this file at startup and uses the values instead of hardcoded constants. If the file is missing, a default one is generated.

## Overview

- **Config format**: TOML (supports # comments natively, clean hierarchical syntax, built-in Python 3.11+ via tomllib)
- **Files involved**:
  - Create: `balance.toml`
  - Modify: `game.py`
  - Modify: `test_game.py`
- **Related patterns**: Existing module-level constants and dicts in game.py (ENEMY_TYPES, WAVE_COMPOSITION, STAT_UPGRADES, etc.)
- **Dependencies**: tomllib (stdlib Python 3.11+), tomli as fallback for older Python

### Sections in balance.toml
- `[player]` - HP, speed, shoot cooldown, radius, ally stats
- `[weapons.default]` - base weapon stats (damage, fire_rate, bullet_speed, range)
- `[weapons.shotgun]` - pellet count, spread angle
- `[weapons.explosive]` - explosion radius
- `[bullets.enemy]` - enemy bullet speed, radius, lifetime
- `[enemies.basic]`, `[enemies.runner]`, `[enemies.brute]`, etc. - per-type HP, speed, radius, color, XP, special behavior
- `[enemies.scaling]` - HP/speed/damage/XP scaling formulas per wave
- `[enemies.shooter]` - cooldown, approach/retreat/firing distances
- `[waves]` - composition weights per wave bracket, wave timer, spawn intervals
- `[upgrades]` - stat upgrade amounts, level scaling thresholds
- `[xp]` - leveling formula coefficients
- `[health_pickups]` - drop chances per enemy type, pickup radius/lifetime/attract range
- `[difficulty]` - max enemies base/cap, spawn count formula
- `[splitter]` - number of minis, spawn offset

## Implementation Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Create balance.toml and add config loading

**Files:**
- Create: `balance.toml`
- Modify: `game.py`

- [x] Create balance.toml with all default values organized into sections, with descriptive comments explaining each value
- [x] Add load_balance_config() function to game.py that reads balance.toml using tomllib (Python 3.11+) with tomli fallback
- [x] If balance.toml is missing, generate one with defaults and a note at the top
- [x] Store loaded config in a module-level BALANCE dict accessible throughout game.py
- [x] Call load_balance_config() early in game initialization (before init_pygame or at module level)
- [x] Write tests for config loading (valid file, missing file generates default)
- [x] Run project test suite - must pass before Task 2

## Task 2: Wire up enemy types and wave composition

**Files:**
- Modify: `game.py`

- [x] Replace ENEMY_TYPES dict with values loaded from BALANCE config
- [x] Replace WAVE_COMPOSITION dict with values from config
- [x] Replace enemy scaling formulas (HP, speed, damage, XP) with config-driven parameters
- [x] Replace shooter behavior constants (cooldown, distances) with config values
- [x] Replace splitter spawn constants with config values
- [x] Replace HEALTH_DROP_CHANCE with config values
- [x] Update tests for enemy/wave config usage
- [x] Run project test suite - must pass before Task 3

## Task 3: Wire up weapons, upgrades, player stats, and difficulty

**Files:**
- Modify: `game.py`

- [x] Replace default_weapon_stats() values with config lookups
- [x] Replace shotgun pellet count/spread and explosive radius with config values
- [x] Replace enemy bullet constants with config values
- [x] Replace STAT_UPGRADES amounts and level scaling thresholds with config values
- [x] Replace player/unit stats (HP, speed, cooldown, radius, ally lifetime) with config values
- [x] Replace XP threshold formula coefficients with config values
- [x] Replace difficulty values (max enemies, spawn interval, wave timer) with config values
- [x] Replace health pickup stats (radius, lifetime, attract range/speed) with config values
- [x] Update tests for weapon/upgrade/player config usage
- [x] Run project test suite - must pass before Task 4

## Task 4: Final integration and testing

**Files:**
- Modify: `test_game.py`

- [ ] Ensure all existing tests pass with the config system
- [ ] Add test that game works with default balance.toml
- [ ] Add test that missing balance.toml generates a default file
- [ ] Run full test suite

## Verification

- [ ] Manual test: start the game, verify gameplay is identical to before
- [ ] Manual test: modify a value in balance.toml, restart, verify it takes effect
- [ ] Manual test: delete balance.toml, verify it regenerates with defaults
- [ ] Run full test suite
- [ ] Run linter if available

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
