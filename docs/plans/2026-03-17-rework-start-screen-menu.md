# Rework Start Screen with Neon Fractal Background and Half-Life Style Menu

Rework the start screen with an animated neon fractal building background and Half-Life style left-aligned clickable menu.

## Context

- Files involved: game.py
- Related patterns: existing draw_menu(), STATE_MENU handling, neon color scheme (cyan/purple/red)
- Dependencies: none (pygame only)

## Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Task 1: Animated neon fractal city background

**Files:**
- Modify: `game.py`

- [ ] Create a FractalBackground class that generates and animates a neon cityscape/building skyline using procedural generation (rectangles of varying height with glowing neon edges, animated scanlines or pulse effects)
- [ ] The background should animate smoothly at 60fps using time-based animation (pygame.time.get_ticks)
- [ ] Use the existing neon color palette (cyan, purple, red glows) with subtle color cycling
- [ ] Instantiate the background once and call its draw method in draw_menu()
- [ ] Write tests for FractalBackground initialization and that draw method is callable
- [ ] Run project test suite - must pass before task 2

## Task 2: Half-Life style left-aligned clickable menu

**Files:**
- Modify: `game.py`

- [ ] Replace current centered menu text with left-aligned menu items positioned at roughly x=60, vertically centered on left side
- [ ] Menu items: NEW GAME, OPTIONS, QUIT - rendered in large bold font with Half-Life style (white/orange text, highlight on hover)
- [ ] Add hover detection using pygame mouse position - highlighted item gets neon glow effect and slight indent
- [ ] Add click handling in the main event loop for STATE_MENU mouse clicks on menu items
- [ ] Keep keyboard navigation working (up/down arrows to select, enter to confirm)
- [ ] Move title text to upper-left area above menu items
- [ ] Update draw_menu() to use new menu rendering
- [ ] Write tests for menu item hover detection and click region calculation
- [ ] Run project test suite - must pass before task 3

## Task 3: Polish and integration

**Files:**
- Modify: `game.py`

- [ ] Add subtle animated line/separator between menu items (like Half-Life's orange line accents)
- [ ] Add smooth fade-in when entering menu state
- [ ] Ensure ESC from options/playing returns to the new menu correctly
- [ ] Write tests verifying state transitions still work
- [ ] Run project test suite - must pass

## Verification

- [ ] Manual test: launch game, verify animated background renders smoothly
- [ ] Manual test: hover over menu items, verify glow/highlight effect
- [ ] Manual test: click each menu item, verify correct action
- [ ] Manual test: keyboard navigation still works
- [ ] Run full test suite: `python -m pytest test_game.py`
- [ ] Verify test coverage meets 80%+

## Wrap-up

- [ ] Move this plan to `docs/plans/completed/`
