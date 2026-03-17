# Options Menu on Start Screen

Add an Options menu accessible from the start screen with resolution selector and fullscreen toggle. Follows the existing neon glow UI aesthetic from the upgrade panel.

## Context

- Files involved: game.py, test_game.py
- Related patterns: upgrade panel UI (draw_glow, centered panel with neon border), state machine for menu navigation
- Dependencies: none (pygame only)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- Follow existing neon glow aesthetic and panel patterns from upgrade menu
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Add Options menu state and resolution/fullscreen settings

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [x] Add STATE_OPTIONS constant alongside existing states
- [x] Add supported resolutions list (e.g. 800x600, 1024x768, 1280x720, 1920x1080)
- [x] Add settings variables: selected_resolution_index, fullscreen flag
- [x] Draw Options menu screen using the upgrade panel UI pattern (centered panel, neon border, glow layers)
- [x] Show resolution options with current selection highlighted
- [x] Show fullscreen toggle (On/Off) with current state highlighted
- [x] Add a "Back" option to return to main menu
- [x] Handle keyboard input: up/down to navigate, left/right or enter to change values, escape to go back
- [x] Apply resolution change via pygame.display.set_mode when changed
- [x] Update WIDTH/HEIGHT globals when resolution changes so game rendering adapts
- [x] Write tests for options menu state transitions and setting changes
- [x] Run project test suite - must pass before task 2

## Task 2: Add Options entry point from start screen

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [ ] Modify draw_menu() to show "Press O for Options" alongside the existing "Press ENTER to Start"
- [ ] Handle O key press in menu state to transition to STATE_OPTIONS
- [ ] Write tests for menu-to-options navigation
- [ ] Run project test suite - must pass

## Verification

- [ ] Manual test: launch game, press O, change resolution, toggle fullscreen, press escape to return
- [ ] Run full test suite: `python -m pytest test_game.py`
- [ ] Run linter if configured
- [ ] Verify test coverage meets 80%+

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
