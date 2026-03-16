# Tron-Style Neon Glow Visual Overhaul

Tron-style visual overhaul for Squad Survivors - neon glow effects with blue, purple, and red color palette, dark background, glowing grid lines, and neon trails/outlines on all game entities.

## Context

- Files involved: game.py, test_game.py
- Related patterns: existing color constants and draw methods
- Dependencies: none (pygame already supports the needed drawing primitives)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Tasks

### Task 1 - Tron color palette and glow helper

**Files:**
- Modify: `game.py` (color constants + new glow utility function)

- [x] Replace all color constants (BG, PLAYER_COLOR, ALLY_COLORS, ENEMY_COLOR, BULLET_COLOR, HEALTH_BG, HEALTH_FG, GRID_COLOR, BORDER_COLOR, OBSTACLE_COLOR, OBSTACLE_BORDER) with Tron neon palette:
  - BG: near-black (5, 5, 15)
  - PLAYER_COLOR: bright cyan (0, 220, 255)
  - ALLY_COLORS: mix of blue, purple, magenta tones
  - ENEMY_COLOR: neon red (255, 30, 60)
  - BULLET_COLOR: bright white-cyan (200, 255, 255)
  - GRID_COLOR: dim blue (15, 15, 40)
  - BORDER_COLOR: neon purple (150, 0, 255)
  - OBSTACLE_COLOR: dark (15, 10, 30)
  - OBSTACLE_BORDER: neon purple (120, 0, 200)
  - HEALTH_FG: neon green-cyan (0, 255, 180)
- [x] Add a draw_glow helper function that draws layered transparent circles to simulate neon glow (using a small Surface with alpha)
- [x] Write tests for the glow helper function
- [x] Run project test suite - must pass before task 2

### Task 2 - Neon glow on entities (player, allies, enemies, bullets)

**Files:**
- Modify: `game.py` (Unit.draw, Enemy.draw, Bullet.draw methods)

- [x] Update Unit.draw to render a neon glow aura behind the unit circle using the glow helper, with a bright outline instead of white
- [x] Update Enemy.draw to render neon red glow behind the diamond shape
- [x] Update Bullet.draw to render small glow around bullets
- [x] Update Obstacle.draw to use neon border glow
- [x] Write tests verifying draw methods run without error with new visuals
- [x] Run project test suite - must pass before task 3

### Task 3 - Neon grid, menus, and HUD

**Files:**
- Modify: `game.py` (draw_grid, draw_menu, draw_game_over, level-up screen, HUD section)

- [x] Update draw_grid to render glowing grid lines (slightly brighter lines with subtle bloom)
- [x] Update draw_menu with neon-styled title (cyan glow) and prompt text
- [x] Update draw_game_over with neon red glow on "GAME OVER" text
- [x] Update level-up screen with neon purple/blue styling
- [x] Update HUD text and XP bar to use neon colors
- [x] Write tests for menu/HUD rendering
- [x] Run project test suite - must pass

## Verification

- [x] Manual test: launch game, verify neon glow on all entities, grid, menus
- [x] Manual test: verify performance is acceptable (glow rendering can be expensive)
- [x] Run full test suite
- [x] Run linter if configured

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
