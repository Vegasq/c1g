# Floating Upgrade Selector Panel

Redesign the level-up upgrade selector from a fullscreen text list into a floating neon-styled panel overlay with icons and mouse click support. The game continues to render behind the panel.

## Context

- Files involved: game.py, test_game.py
- Related patterns: draw_glow() for neon effects, SRCALPHA surfaces for transparency, existing neon color palette
- Dependencies: none (Pygame only)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

---

## Task 1 - Render game behind upgrade selector instead of filling screen

**Files:**
- Modify: `game.py`

- [x] In the STATE_LEVEL_UP branch (lines 580-597), remove the screen.fill(BG) call
- [x] Instead, let the normal game drawing code run first (map, units, enemies, HUD), then draw the upgrade panel on top
- [x] Add a semi-transparent dark overlay (SRCALPHA surface at ~60% opacity) over the game to dim it behind the panel
- [x] Write tests verifying the game state still renders during level-up
- [x] Run project test suite - must pass before task 2

## Task 2 - Create floating upgrade panel with neon border

**Files:**
- Modify: `game.py`

- [x] Draw a centered panel rectangle (~500x350px) with semi-transparent dark background
- [x] Add neon glow border around the panel using the existing draw_glow pattern and BORDER_COLOR
- [x] Render "Level Up!" title and upgrade options inside the panel instead of at screen center
- [x] Position upgrade options as card-like rows within the panel (each option gets its own rectangular area with hover highlight)
- [x] Write tests for panel dimensions and positioning
- [x] Run project test suite - must pass before task 3

## Task 3 - Add icons to upgrades

**Files:**
- Modify: `game.py`

- [x] Create simple procedural icons using Pygame drawing (no external image files): sword for damage, lightning bolt for fire rate, arrow for bullet speed, crosshair for range, special shapes for weapon types (shotgun spread, piercing line, explosion circle)
- [x] Draw each icon as a small (32x32) SRCALPHA surface using lines, circles, and polygons in neon colors
- [x] Display the icon to the left of each upgrade name in the panel
- [x] Write tests verifying icons are created for each upgrade type
- [x] Run project test suite - must pass before task 4

## Task 4 - Add mouse click support

**Files:**
- Modify: `game.py`

- [ ] Track mouse position during STATE_LEVEL_UP to detect which upgrade option the cursor hovers over
- [ ] Add hover visual feedback (brighter border or glow on the hovered option row)
- [ ] Handle MOUSEBUTTONDOWN events to select the hovered upgrade on click
- [ ] Keep existing keyboard (1/2/3) selection as alternative input
- [ ] Write tests for click detection and hover state logic
- [ ] Run project test suite - must pass before task 5

---

## Final Validation

- [ ] Manual test: level up in game, verify panel floats over gameplay, icons display, clicking works
- [ ] Run full test suite: `python -m pytest test_game.py`
- [ ] Run linter if configured
- [ ] Verify test coverage meets 80%+

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
