# Upgrade Panel Card-Based UI Overhaul

## Overview
Replace the current list-style upgrade panel with a card-based layout showing three upgrade cards side by side. Each card uses the upgrades_card.png image as background, loads upgrade icons from PNG files, and displays title/body/level text positioned according to upgrades_card.toml. Cards scale up slightly on hover.

## Context
- Files involved:
  - `game.py` (lines 2172-2322): Panel constants, `create_upgrade_icon`, `draw_upgrade_panel`, `_panel_origin`, `get_hovered_upgrade_index`
  - `assets/upgrades/upgrades_card.png`: Card background image (tall card with icon frame, title, body, level sections)
  - `assets/upgrades/upgrades_card.toml`: Position config (icon center: 202,218; title: 202,38; body: 202,483; level: 202,621)
  - `assets/upgrades/upgrades_*.png`: Individual upgrade icons (max_hp, move_speed, weapon_normal, weapon_shotgun, weapon_piercing, weapon_explosive, ally_spawn, heal_amount)
  - `progression.py`: UPGRADE_CATEGORIES dict with name, description, format_value, compute per category
- Screen size: 1024x768, card image is approximately 404x660+ px based on TOML coordinates
- Upgrade options always have 3 choices with fields: category, name, current_level, is_unlock
- Related patterns: existing hover detection via `get_hovered_upgrade_index`, `level_up_selected_index` for keyboard/gamepad

## Development Approach
- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Implementation Steps

### Task 1: Load card assets and update constants

**Files:**
- Modify: `game.py`

- [x] Load `upgrades_card.png` as a pygame surface at init time (alongside other asset loading)
- [x] Parse `upgrades_card.toml` to get icon/title/body/level center positions
- [x] Calculate card dimensions from the loaded card image surface
- [x] Calculate scale factor so 3 cards fit horizontally on screen with gaps (e.g., target card width ~250-280px with ~20px gaps)
- [x] Update panel constants: PANEL_WIDTH to fit 3 scaled cards + margins, PANEL_HEIGHT to fit scaled card height + title area, remove old OPTION_ROW_HEIGHT/OPTION_START_Y/ICON_SIZE
- [x] Pre-scale the TOML positions by the same scale factor for rendering
- [x] Write tests verifying asset loading and TOML parsing produce valid values
- [x] Run project test suite - must pass before task 2

### Task 2: Rewrite create_upgrade_icon to load PNGs

**Files:**
- Modify: `game.py`

- [x] Replace procedural icon generation in `create_upgrade_icon` with loading `assets/upgrades/upgrades_{category}.png`
- [x] Scale loaded icon to fit the icon area on the scaled card
- [x] Cache loaded icons to avoid reloading each frame
- [x] Write tests verifying icons load correctly for all 8 categories
- [x] Run project test suite - must pass before task 3

### Task 3: Rewrite draw_upgrade_panel for card layout

**Files:**
- Modify: `game.py`

- [x] Draw a dark semi-transparent overlay behind the panel (reuse existing draw_dim_overlay or similar)
- [x] Draw the "Level N!" title centered above the three cards
- [x] For each of the 3 upgrade options, blit the scaled card image side by side with spacing
- [x] On each card, blit the upgrade icon centered at the scaled icon position from TOML
- [x] For title: render `opt["name"]` (the label text) and center it at the scaled title position
- [x] For body: render the description text from `UPGRADE_CATEGORIES[category]["description"]` and center it at the scaled body position
- [x] For new value: compute the difference between current and next level values using `format_value`, render it in green color, and position it on the card (below body or as part of body area)
- [x] For level: render "LEVEL {cur_lv + 1}" or "UNLOCK" if is_unlock, center at the scaled level position
- [x] Write tests verifying draw_upgrade_panel runs without errors with mock upgrade options
- [x] Run project test suite - must pass before task 4

### Task 4: Implement hover card scaling effect

**Files:**
- Modify: `game.py`

- [ ] When a card is hovered (matches `level_up_selected_index`), scale that card's surface up slightly (e.g., 1.05-1.1x) before blitting
- [ ] Non-hovered cards remain at default scale
- [ ] Adjust blit position for scaled card so it stays centered in its slot
- [ ] Write tests verifying hover index detection works with new card-based layout
- [ ] Run project test suite - must pass before task 5

### Task 5: Update get_hovered_upgrade_index for card layout

**Files:**
- Modify: `game.py`

- [ ] Replace row-based hit detection with card-based hit detection: check if mouse position falls within any of the 3 card rectangles
- [ ] Account for the new panel origin and card positions
- [ ] Write tests verifying hover detection returns correct index for each card area and -1 for gaps
- [ ] Run project test suite - must pass before task 6

### Task 6: Verify acceptance criteria

- [ ] Run full test suite
- [ ] Run linter
- [ ] Visually verify: 3 cards display in a row with correct icons, title, body, value, and level text
- [ ] Visually verify: hovered card scales up, non-hovered cards stay at default size
- [ ] Visually verify: keyboard/gamepad selection still works

### Task 7: Update documentation

- [ ] Update README.md if user-facing changes
- [ ] Update CLAUDE.md if internal patterns changed
- [ ] Move this plan to `docs/plans/completed/`
