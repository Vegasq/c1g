# Fix Options Mouse Support, Upgrades Centering, and Add Stats Collection

## Overview

Fix options menu mouse support, center upgrades popup on all resolutions, and add per-run/per-weapon stats collection to JSON.

Three issues addressed:
1. Options menu has no mouse handlers - add MOUSEMOTION and MOUSEBUTTONDOWN handling mirroring the main menu pattern
2. Upgrades popup PANEL_X/PANEL_Y are computed once at module level and never recalculated when resolution changes - make them dynamic
3. Add stats collection (per-run and per-weapon) saved to a JSON file for balance analysis

- **Files involved**: `game.py`
- **Related patterns**: Main menu mouse handling at ~line 1247 (get_hovered_menu_index), upgrade panel drawing at ~line 1085
- **Dependencies**: None (pygame only)

## Implementation Strategy

- **Testing approach**: Manual testing (pygame game with no test framework)
- Complete each task fully before moving to the next

## Task 1: Add mouse support to the options menu

**Files:**
- Modify: `game.py`

- [ ] Create `get_hovered_options_index()` helper similar to `get_hovered_menu_index()` at ~line 1247
- [ ] Add MOUSEMOTION handler for STATE_OPTIONS that updates `options_selected_index` on hover
- [ ] Add MOUSEBUTTONDOWN handler for STATE_OPTIONS that triggers the same actions as RETURN/LEFT/RIGHT keys (cycle resolution, toggle fullscreen, go back)
- [ ] For Resolution and Fullscreen items, left-click cycles forward (same as RIGHT key)
- [ ] Manual test: verify options menu items highlight on hover, clicking Resolution cycles values, clicking Fullscreen toggles, clicking Back returns to main menu

## Task 2: Fix upgrades popup centering on all resolutions

**Files:**
- Modify: `game.py`

- [ ] Replace module-level `PANEL_X`/`PANEL_Y` constants with dynamic calculation using current `WIDTH`/`HEIGHT`
- [ ] Compute panel position at draw time in `draw_upgrade_panel()` and `get_hovered_upgrade_index()`
- [ ] Manual test: verify upgrades popup is centered at multiple resolutions (change resolution in options, trigger upgrade popup)

## Task 3: Add stats collection system

**Files:**
- Modify: `game.py`
- Created at runtime: `stats.json`

- [ ] Add tracking variables for damage dealt, damage taken, and weapon usage during gameplay
- [ ] Create a `collect_run_stats()` function that gathers per-run data: kills, damage dealt, damage taken, waves reached, survival time, weapons used, XP earned
- [ ] Create a `collect_weapon_stats()` function that gathers per-weapon data: times picked, total damage, total kills
- [ ] Save stats to `stats.json` in the game directory, appending each run as a new entry in a JSON array
- [ ] Call stats collection at game over (STATE_GAME_OVER transition)
- [ ] Manual test: verify `stats.json` is created after a game over with correct structure

## Final Validation

- [ ] Manual test: all three features work together without regressions
- [ ] Run full game loop: start game, reach upgrade popup (verify centered), open options (verify mouse works), play until game over (verify stats saved)

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
