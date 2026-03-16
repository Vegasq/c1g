# Enemy Variety and Weapon Scaling

Add tiered enemy progression with unique behaviors per type, wave-based unlocking/replacement of enemy tiers, and weapon upgrade scaling to match increasing enemy difficulty.

## Overview

Enemy tiers:
- Tier 1 (waves 1-5): Basic (current diamond enemy, HP=2, speed=1.2)
- Tier 2 (waves 3+): Runner (smaller, faster, lower HP) and Brute (larger, slower, high HP)
- Tier 3 (waves 6+): Shielded (absorbs first hit, then normal) and Splitter (splits into 2 mini-enemies on death)
- Tier 4 (waves 10+): Elite (fast, high HP, larger, glows differently)

Wave composition: as new tiers unlock, spawn weights shift - older tiers gradually become rarer and eventually stop spawning entirely.

Weapon scaling: increase upgrade amounts at higher levels and add a new "scaling factor" so upgrades grow stronger as enemy HP rises. Milestone weapon upgrades remain at every 5 levels.

- **Files involved:**
  - Modify: `game.py` (Enemy class, spawn logic, wave system, upgrade scaling)
  - Modify: `test_game.py` (tests for new enemy types, spawn composition, upgrade scaling)
- **Related patterns:** existing Enemy class, Bullet damage system, STAT_UPGRADES, wave/spawn loop
- **Dependencies:** none

## Approach

- **Testing approach:** Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Tasks

### Task 1: Refactor Enemy class to support types

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add enemy_type parameter to Enemy.__init__ with a config dict mapping type names to stats (hp, speed, radius, color, xp_value)
- [x] Define ENEMY_TYPES config dict with "basic" type matching current stats
- [x] Update Enemy.draw to use per-type color
- [x] Add xp_value per enemy type (basics=1, tougher enemies give more)
- [x] Update kill logic to use enemy.xp_value instead of hardcoded 1
- [x] Write tests for enemy type creation, stat assignment, and xp values
- [x] Run test suite - must pass before task 2

### Task 2: Add tier 2 enemy types (Runner and Brute)

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add "runner" to ENEMY_TYPES: radius=8, speed=2.2, hp=1, color=neon yellow, xp=1
- [x] Add "brute" to ENEMY_TYPES: radius=18, speed=0.7, hp=6, color=neon orange, xp=3
- [x] Update Enemy.draw to render different shapes per type (runner=triangle, brute=hexagon)
- [x] Write tests for runner and brute creation and rendering
- [x] Run test suite - must pass before task 3

### Task 3: Add tier 3 enemy types (Shielded and Splitter)

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add "shielded" to ENEMY_TYPES: radius=14, speed=1.0, hp=4, color=neon cyan, xp=4, has shield attribute
- [x] Implement shield behavior: first hit removes shield (visual change) instead of dealing damage
- [x] Add "splitter" to ENEMY_TYPES: radius=14, speed=1.0, hp=3, color=neon green, xp=2
- [x] Implement split-on-death: when splitter dies, spawn 2 "mini" enemies (radius=7, speed=1.8, hp=1)
- [x] Add "mini" to ENEMY_TYPES for splitter children (no further splitting)
- [x] Write tests for shield mechanic and split-on-death behavior
- [x] Run test suite - must pass before task 4

### Task 4: Add tier 4 enemy type (Elite)

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add "elite" to ENEMY_TYPES: radius=16, speed=1.8, hp=10, color=neon magenta, xp=8
- [x] Give elite a pulsing glow effect in draw method
- [x] Write tests for elite creation and xp value
- [x] Run test suite - must pass before task 5

### Task 5: Wave-based enemy composition and tier replacement

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Create WAVE_COMPOSITION dict mapping wave ranges to spawn weight tables (e.g. wave 1-2: 100% basic, wave 3-5: 60% basic 25% runner 15% brute, etc.)
- [x] At wave 8+, basics stop spawning entirely; tier 2 becomes common, tier 3 mixes in
- [x] At wave 12+, tier 2 becomes rare, tier 3 common, tier 4 elites begin appearing
- [x] Modify spawn loop to select enemy type based on current wave's weight table
- [x] Write tests for spawn composition at different wave numbers
- [x] Run test suite - must pass before task 6

### Task 6: Scale weapon upgrades with enemy progression

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add scaling multiplier to STAT_UPGRADES: after level 10, damage upgrades give +2 instead of +1; after level 20, +3
- [x] After level 15, fire rate upgrades give -5 instead of -3
- [x] Increase frequency of weapon type offerings at higher levels (every 4 levels instead of 5 after level 15)
- [x] Write tests for scaled upgrade amounts at different player levels
- [x] Run test suite - must pass before task 7

### Task 7: Final validation

- [x] Manual test: play through waves 1-15 and verify enemy variety progression
- [x] Run full test suite
- [x] Verify all enemy types spawn at correct waves
- [x] Verify weapon upgrades feel adequate against tougher enemies

## Post-completion

- [ ] Move this plan to `docs/plans/completed/`
