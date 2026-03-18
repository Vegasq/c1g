# Add Gamepad Support for Steam Deck

Add gamepad/controller support to Squad Survivors so all game interactions can be performed with a Steam Deck controller. The game already auto-aims, so gamepad support covers: movement (left stick + D-pad), menu navigation, and confirm/back buttons. Keyboard+mouse input remains fully functional alongside gamepad.

## Overview

Button mapping (SDL/Steam Deck standard):
- Left stick / D-pad: Movement (gameplay) and navigation (menus)
- A button (SDL 0): Confirm / Select (replaces Enter / mouse click)
- B button (SDL 1): Back / Escape
- D-pad left/right: Adjust options values
- D-pad up/down + A: Select upgrades in level-up screen

- **Files involved**: `game.py`, `test_game.py`
- **Related patterns**: Existing event loop in `game.py` (lines 1608-1707), continuous input polling (lines 1734-1753)
- **Dependencies**: `pygame.joystick` (already bundled with pygame, no new dependencies)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- All gamepad input integrates into existing event loop and input polling - no separate input system
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Gamepad initialization and detection

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [ ] Initialize `pygame.joystick` subsystem at game startup (near existing `pygame.init`)
- [ ] Add global variable to track active joystick instance
- [ ] Handle `JOYDEVICEADDED` and `JOYDEVICEREMOVED` events in the main event loop to support hot-plugging
- [ ] Add analog stick deadzone constant (e.g. 0.3)
- [ ] Write tests for joystick initialization and device add/remove handling
- [ ] Run project test suite - must pass before task 2

## Task 2: Gamepad movement during gameplay

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [ ] Read left analog stick axes (axis 0 = horizontal, axis 1 = vertical) during `STATE_PLAYING`, apply deadzone, and combine with existing keyboard mx/my movement
- [ ] Read D-pad (hat 0) during `STATE_PLAYING` and combine with movement
- [ ] Normalize combined movement vector (same as existing keyboard normalization)
- [ ] Write tests for gamepad movement input handling
- [ ] Run project test suite - must pass before task 3

## Task 3: Gamepad support for all menu and UI states

**Files:**
- Modify: `game.py`
- Modify: `test_game.py`

- [ ] `STATE_MENU`: D-pad up/down or left stick to change selected menu item, A button to confirm selection, B button to quit
- [ ] `STATE_OPTIONS`: D-pad up/down to navigate options, D-pad left/right to change values (resolution, fullscreen), A button on "Back" to return, B button as shortcut to return
- [ ] `STATE_LEVEL_UP`: D-pad up/down to highlight upgrade (add keyboard-style selection index if not present), A button to select highlighted upgrade
- [ ] `STATE_GAME_OVER`: A button to start new game (replaces Enter), B button to return to menu (replaces Escape)
- [ ] Add repeat-delay for D-pad/stick menu navigation to prevent too-fast scrolling
- [ ] Write tests for gamepad menu interactions across all states
- [ ] Run project test suite - must pass before task 4

## Task 4: Final validation

- [ ] Manual test: connect a controller and navigate full game flow (menu -> options -> back -> new game -> play -> level up -> select upgrade -> die -> game over -> menu)
- [ ] Manual test: verify hot-plug works (connect/disconnect controller during gameplay)
- [ ] Manual test: verify keyboard+mouse still works with controller connected
- [ ] Run full test suite: `python -m pytest test_game.py`
- [ ] Verify test coverage meets 80%+

## Wrap-up

- [ ] Update `CLAUDE.md` if internal patterns changed
- [ ] Move this plan to `docs/plans/completed/`
