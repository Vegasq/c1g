# Health Pickups and Max HP Upgrades

## Overview

Add health pickups that enemies randomly drop on death, plus a health upgrade option in the level-up screen. Pickups auto-collect when the player walks near them (like XP orbs in Vampire Survivors).

- **Files involved**: `game.py`, `test_game.py`
- **Related patterns**: Enemy death handler, Unit class HP system, ally spawn on kill (10% chance), level-up upgrade options
- **Dependencies**: None

## Implementation Strategy

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

---

## Task 1 - Health Pickup Entity

**Files:**
- Modify: `game.py`

- [ ] Create a `HealthPickup` class with `x`, `y`, `radius`, `heal_amount`, and a lifetime timer
- [ ] Add neon green glow rendering (to distinguish from other entities)
- [ ] Add attraction behavior: when player is within ~100px, pickup moves toward player; collected on contact
- [ ] Write tests for HealthPickup creation, attraction movement, and collection
- [ ] Run project test suite - must pass before Task 2

## Task 2 - Drop System on Enemy Death

**Files:**
- Modify: `game.py`

- [ ] In the enemy death handler, add a random chance (e.g. 5-8%) to spawn a HealthPickup at enemy position
- [ ] Higher XP enemies (brute, elite) get a higher drop chance
- [ ] Add pickup list management (update positions, remove expired/collected)
- [ ] Write tests for drop chance logic and pickup lifecycle
- [ ] Run project test suite - must pass before Task 3

## Task 3 - Collection and Healing

**Files:**
- Modify: `game.py`

- [ ] In the game loop, check player proximity to each pickup for auto-collect
- [ ] On collection, restore 1 HP (capped at max HP)
- [ ] Add a brief visual flash or particle effect on collection
- [ ] Write tests for healing logic and max HP cap
- [ ] Run project test suite - must pass before Task 4

## Task 4 - Max HP Upgrade in Level-Up Screen

**Files:**
- Modify: `game.py`

- [ ] Add a new upgrade option "+Max HP" to the level-up choices (alongside existing stat upgrades)
- [ ] When selected, increase player max HP by 1 and heal 1 HP
- [ ] Write tests for the upgrade option and its effect
- [ ] Run project test suite - must pass before final validation

---

## Final Validation

- [ ] Manual test: kill enemies and verify green health pickups drop and auto-collect
- [ ] Manual test: level up and verify +Max HP option appears and works
- [ ] Run full test suite
- [ ] Verify test coverage meets 80%+

## Cleanup

- [ ] Update README.md if user-facing changes
- [ ] Update CLAUDE.md if internal patterns changed
- [ ] Move this plan to `docs/plans/completed/`
