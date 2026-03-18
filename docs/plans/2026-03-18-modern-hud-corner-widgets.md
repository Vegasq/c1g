# Modern HUD: Corner Widget Layout

## Overview

Modernize the in-game HUD from a single text line to a corner-widget layout with semi-transparent neon-themed panels in each screen corner.

**Layout:**
- Top-left: Player vitals (HP bar with numeric display, XP bar with level indicator)
- Top-right: Score and wave counter with neon styling
- Bottom-left: Weapon info with type indicators
- Bottom-right: Minimap showing player, allies, enemies, and obstacles

- **Files involved:** `game.py`
- **Related patterns:** Existing neon glow rendering (`draw_glow`), upgrade panel styling (`PANEL_BG_COLOR`), color constants (`PLAYER_COLOR`, `BORDER_COLOR`, `HEALTH_FG`)
- **Dependencies:** None (pure Pygame rendering)

## Implementation approach

- **Testing approach:** Manual visual testing (UI rendering changes)
- Keep all code in `game.py` following the existing single-file pattern
- Reuse existing color constants and neon theme
- Support dynamic positioning based on screen resolution (`WIDTH`, `HEIGHT`)
- Remove the old single-line HUD and XP bar, replace with new widget system

## Task 1: Create HUD panel helper and top-left vitals widget

**Files:**
- Modify: `game.py`

- [x] Add a `draw_hud_panel()` helper that renders a semi-transparent rounded rect with neon border (reuse `PANEL_BG_COLOR` style)
- [x] Add `draw_hud_vitals()` function: HP bar (wider, labeled, with numeric "3/5"), XP bar (with level badge), positioned top-left
- [x] Remove old HUD text line and old XP bar from `draw_game_scene()`
- [x] Call `draw_hud_vitals()` from `draw_game_scene()`
- [x] Manual test: verify vitals widget renders correctly and old HUD is removed

## Task 2: Create top-right score/wave widget and bottom-left weapon widget

**Files:**
- Modify: `game.py`

- [x] Add `draw_hud_stats()` function: Score with neon text, Wave counter, Squad size - positioned top-right
- [x] Add `draw_hud_weapons()` function: List active weapons with colored type indicators - positioned bottom-left
- [x] Call both from `draw_game_scene()`
- [x] Manual test: verify both widgets render correctly and don't overlap with gameplay

## Task 3: Create bottom-right minimap widget

**Files:**
- Modify: `game.py`

- [x] Add `draw_hud_minimap()` function: Small panel showing scaled-down map with dots for player (cyan), allies (blue), enemies (red), and obstacle outlines
- [x] Scale world coords (`MAP_WIDTH` x `MAP_HEIGHT`) down to minimap size (~150x112px)
- [x] Draw semi-transparent background with neon border
- [x] Call from `draw_game_scene()`, passing camera, player, allies, enemies, obstacles
- [x] Manual test: verify minimap shows correct positions and updates in real-time

## Task 4: Resolution-aware positioning and visual polish

**Files:**
- Modify: `game.py`

- [x] Ensure all widget positions use `WIDTH`/`HEIGHT` constants for proper placement at all supported resolutions
- [x] Add subtle glow effects to panel borders using existing `draw_glow` pattern
- [x] Verify all four widgets render correctly at 800x600, 1024x768, 1280x720, and 1920x1080
- [x] Manual test: play a few waves and confirm readability and no overlap with gameplay

## Validation checklist

- [x] Manual test: play through multiple waves and verify all HUD elements update correctly
- [x] Manual test: verify HUD is readable during intense gameplay (many enemies on screen)
- [x] Run linter if configured
- [x] Verify no regression in game performance (HUD rendering should be lightweight)

## Wrap-up

- [ ] Update README.md if user-facing changes
- [ ] Update CLAUDE.md if internal patterns changed
- [ ] Move this plan to `docs/plans/completed/`
