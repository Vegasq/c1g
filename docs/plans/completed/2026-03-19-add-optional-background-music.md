# Add Optional Background Music

Add optional background music support. The game will look for `menu.wav` and `game.wav` next to `game.py` and loop them during the appropriate game states.

## Context

- Files involved: `game.py`, `test_game.py`
- Related patterns: File lookup uses `os.path.dirname(os.path.abspath(__file__))` (same as `BALANCE_FILE`, `STATS_FILE`)
- Dependencies: None (`pygame.mixer` is part of pygame)

## Implementation approach

- **Testing approach**: Regular (code first, then tests)
- Music file paths derived from `__file__` like existing config files
- Graceful handling when wav files are missing or mixer unavailable
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Add music infrastructure

**Files:**
- Modify: `game.py`

- [x] Add `MUSIC_DIR` constant using `os.path.dirname` pattern (same as `BALANCE_FILE`)
- [x] Add a helper function (e.g. `_play_music(filename)`) that checks if the wav file exists, and if so loads and loops it via `pygame.mixer.music`. If the file does not exist or mixer is not available, silently do nothing.
- [x] Add a helper function (e.g. `_stop_music()`) to stop current playback
- [x] Write tests for the new helper functions (file exists/missing, mixer available/unavailable)
- [x] Run project test suite - must pass before task 2

## Task 2: Integrate music with game state transitions

**Files:**
- Modify: `game.py`

- [x] In `run()`, after `init_pygame()`, call `_play_music("menu.wav")` to start menu music
- [x] On state transition to `STATE_PLAYING` (new game start, restart from game over), switch to `_play_music("game.wav")`
- [x] On state transition to `STATE_MENU` (escape from playing, game over escape, options back), switch to `_play_music("menu.wav")`
- [x] On `STATE_GAME_OVER`, keep `game.wav` playing (simpler, still in-game feel)
- [x] On `STATE_LEVEL_UP`, keep `game.wav` playing (still in-game)
- [x] Write tests verifying music switches happen on state transitions
- [x] Run project test suite - must pass

## Verification

- [x] manual test: drop `menu.wav` and `game.wav` next to `game.py`, verify music loops in menu and switches on game start
- [x] manual test: remove wav files, verify game runs without errors
- [x] run full test suite: `python -m pytest test_game.py`
- [x] run linter if configured
- [x] verify test coverage meets 80%+

## Wrap-up

- [x] update README.md if user-facing changes
- [x] update CLAUDE.md if internal patterns changed
- [x] move this plan to `docs/plans/completed/`
