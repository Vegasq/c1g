# Fullscreen Display Resolution Detection

Detect the native display resolution at startup using Pygame's display info API, default to fullscreen mode, and persist display settings between sessions.

## Context

- **Files involved**: `game.py`, `settings.json` (new - created at runtime for persisting display preferences)
- **Related patterns**: `stats.json` already used for persistence; `apply_resolution()` handles fullscreen with fallback
- **Dependencies**: None (Pygame already provides display detection APIs)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1 - Detect native display resolution and use it as default

**Files:**
- Modify: `game.py`

- [ ] In `init_pygame()`, before calling `pygame.display.set_mode()`, use `pygame.display.Info()` (called before `set_mode` to get desktop resolution) to detect the native monitor resolution
- [ ] Add the native resolution to `SUPPORTED_RESOLUTIONS` if not already present, and set it as the default selection
- [ ] Change `options_fullscreen` default to `True` so the game starts in fullscreen
- [ ] Update `apply_resolution()` to handle the dynamically added native resolution
- [ ] Write tests verifying resolution detection logic and that native resolution is added to the supported list
- [ ] Run project test suite - must pass before task 2

## Task 2 - Persist display settings between sessions

**Files:**
- Modify: `game.py`
- Create: `settings.json` (created at runtime, not committed)

- [ ] Add `save_settings()` function that writes current resolution index, fullscreen flag, and the selected resolution tuple to a `settings.json` file (alongside existing `stats.json`)
- [ ] Add `load_settings()` function that reads `settings.json` on startup and applies saved preferences, falling back to auto-detected defaults if file is missing or invalid
- [ ] Call `save_settings()` in `apply_resolution()` so changes are persisted when the user modifies them in the options menu
- [ ] Call `load_settings()` in `init_pygame()` before window creation
- [ ] Write tests for save/load settings round-trip and fallback behavior
- [ ] Run project test suite - must pass before task 3

## Task 3 - Ensure proper fullscreen initialization on startup

**Files:**
- Modify: `game.py`

- [ ] Restructure `init_pygame()` to: (1) init pygame, (2) detect display, (3) load saved settings or use detected defaults, (4) create window with correct flags
- [ ] Ensure the initial `set_mode` call uses `pygame.FULLSCREEN` flag when fullscreen is the active setting
- [ ] Verify the fallback in `apply_resolution()` still works if fullscreen fails on startup
- [ ] Write tests for the initialization sequence
- [ ] Run project test suite - must pass

## Verification

- [ ] Manual test: launch game, verify it starts fullscreen at native resolution
- [ ] Manual test: change resolution in options menu, restart game, verify settings are remembered
- [ ] Manual test: delete `settings.json`, restart game, verify it auto-detects and starts fullscreen
- [ ] Run full test suite
- [ ] Run linter if configured

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
