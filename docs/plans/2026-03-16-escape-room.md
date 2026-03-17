# Escape Room Safe Zone

Add an "Escape Room" safe zone entity to the game. When the player enters the escape room, all enemies currently on screen are eliminated and the escape room teleports to a new random location on the map. Enemies cannot enter the escape room area.

## Context

- Files involved: game.py, test_game.py
- Related patterns: Obstacle class (rectangular entity with collision), HealthPickup (world entity with player proximity detection), Enemy spawning/elimination logic in main loop
- Dependencies: None (pure Pygame, all in game.py)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1 - Create EscapeRoom class

**Files:**
- Modify: `game.py`

- [x] Add EscapeRoom class with properties: x, y, w, h (rectangular, similar to Obstacle), a distinct neon color (e.g. green/teal glow)
- [x] Add draw(camera) method with visibility culling, glow effect, and distinct visual (pulsing border or shimmer to distinguish from obstacles)
- [x] Add collides_circle(cx, cy, radius) method (reuse Obstacle pattern) for detecting player entry and enemy repulsion
- [x] Add relocate(obstacles, escape_rooms) method that picks a new random position on the map (avoiding obstacles and spawn center, similar to obstacle generation logic)
- [x] Write tests for EscapeRoom: construction, collision detection, relocation avoids obstacles

## Task 2 - Integrate EscapeRoom into game loop

**Files:**
- Modify: `game.py`

- [x] Spawn one EscapeRoom during game initialization (alongside obstacles), placed randomly avoiding obstacles
- [x] In the main loop, check if player circle overlaps the escape room (using collides_circle)
- [x] On player entry: eliminate all enemies currently visible on screen (using camera visibility check), award XP for eliminated enemies, trigger health pickup drops per normal drop logic, then call relocate() to move the escape room
- [x] Add enemy repulsion: in the enemy update section, push enemies out of the escape room area (reuse push_circle_out pattern from Obstacle)
- [x] Draw the escape room in the render section (draw before enemies, after grid/obstacles)
- [x] Add visual feedback when escape room triggers (screen flash or particle burst)
- [x] Write tests: player entry triggers elimination, escape room relocates after trigger, enemies are pushed out of escape room area, XP is awarded for eliminated enemies

## Task 3 - Add minimap indicator

**Files:**
- Modify: `game.py`

- [x] Add a small indicator on the HUD or minimap showing the escape room's direction/distance relative to the player (arrow or dot at screen edge pointing toward it when off-screen)
- [x] Write tests for indicator positioning logic

## Verification

- [ ] Manual test: run game, find escape room, enter it, verify enemies die and room relocates
- [ ] Manual test: verify enemies cannot enter the escape room
- [ ] Run full test suite: `python -m pytest test_game.py`
- [ ] Run linter: check with flake8 or project linter
- [ ] Verify test coverage meets 80%+

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
