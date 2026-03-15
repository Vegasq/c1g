# Plan: Scrollable Map, Ally Tuning, Enemy Scaling, Obstacles, Menu

Enhance Squad Survivors with a scrollable 4096x3072 map, camera system, reduced ally conversion (1-in-10), faster enemy scaling, obstacles, and a main menu.

## Context

- Files involved: `game.py`
- Related patterns: pygame sprite-style classes, frame-based timers
- Dependencies: pygame (already installed)

## Approach

- **Testing approach**: Manual testing (single-file pygame game, no test framework in place)
- Complete each task fully before moving to the next
- All changes in `game.py` since it is a single-file game

## Task 1 - Camera system and large map

**Files:**
- Modify: `game.py`

- [x] Add MAP_WIDTH=4096, MAP_HEIGHT=3072 constants
- [x] Create a Camera class that tracks player position and offsets rendering
- [x] Update player movement to use map coordinates (clamp to map bounds instead of screen bounds)
- [x] Update all draw calls to offset by camera position (player, allies, enemies, bullets, health bars)
- [x] Update enemy spawning to spawn at edges of camera view (not map edges)
- [x] Add a simple ground grid or border so the player can see they are moving across the map
- [x] Manual test: player can move across the full map, camera follows smoothly

## Task 2 - Ally conversion rate and expiration

**Files:**
- Modify: `game.py`

- [x] Change ally conversion from all enemies to 1-in-10 chance (use random with 0.1 probability)
- [x] Add a lifetime/timer to allies (e.g. 600 frames / 10 seconds) after which they disappear
- [x] Show ally lifetime visually (e.g. fading color or shrinking health bar as time runs out)
- [x] Manual test: only ~10% of killed enemies become allies, allies disappear after timer

## Task 3 - Faster enemy spawning progression

**Files:**
- Modify: `game.py`

- [ ] Reduce the spawn interval floor (allow it to get faster than current minimum)
- [ ] Increase the rate at which spawn_interval decreases (e.g. decrease by 12 instead of 8 every wave)
- [ ] Increase wave enemy count scaling (e.g. wave grows faster)
- [ ] Manual test: enemy density noticeably increases over 2-3 minutes of play

## Task 4 - Obstacles

**Files:**
- Modify: `game.py`

- [ ] Create an Obstacle class (rectangular or circular static objects on the map)
- [ ] Generate random obstacles at game start (spread across the map, avoid player spawn area)
- [ ] Add collision detection: player and allies cannot walk through obstacles
- [ ] Add collision detection: enemies path around or are blocked by obstacles
- [ ] Bullets are stopped by obstacles
- [ ] Draw obstacles with camera offset
- [ ] Manual test: obstacles block movement and bullets, spread across the large map

## Task 5 - Main menu

**Files:**
- Modify: `game.py`

- [ ] Create a menu screen with "Squad Survivors" title and "Press ENTER to Start" prompt
- [ ] Add game state management (MENU, PLAYING, GAME_OVER)
- [ ] On death, show game over screen with score and "Press ENTER to Restart"
- [ ] ESC from gameplay returns to menu
- [ ] Manual test: full flow from menu to gameplay to death to restart

## Final Verification

- [ ] Manual test: play through full loop (menu, large map traversal, obstacles, ally conversion, enemy scaling, death, restart)
- [ ] Verify no performance issues with large map and many entities
