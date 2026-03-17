# Settings Menu Restyle

Restyle the settings/options menu in game.py to match the main menu's visual style - animated separators, consistent fonts/colors, hover indentation, and the fractal background showing through.

- Files involved: game.py (lines ~1181-1243 for settings menu, ~1260-1335 for main menu reference)
- Related patterns: Main menu styling (animated separators, hover indent, color scheme, glow effects)
- Dependencies: None

## Implementation approach

- **Testing approach**: Manual visual testing (UI styling changes)
- Use the main menu's draw_menu method as the reference for consistent styling
- Complete each task fully before moving to the next

## Tasks

### Task 1 - Restyle settings menu layout and background

**Files:**
- Modify: `game.py` (draw_options_menu method)

- [x] Remove the centered panel/box approach (PANEL_WIDTH, PANEL_HEIGHT, bordered rectangle)
- [x] Let the fractal background show through fully (no opaque panel overlay)
- [x] Add "Options" title using title_font (size 72) with cyan glow, matching main menu title style
- [x] Position menu items left-aligned at MENU_X=60, starting below the title, with MENU_ITEM_HEIGHT=60

### Task 2 - Apply main menu item styling to settings items

**Files:**
- Modify: `game.py` (draw_options_menu method)

- [x] Use menu_font (size 52) for option items instead of smaller font
- [x] Apply same color scheme: selected = orange (255, 140, 0) with white text, unselected = gray (180, 180, 180)
- [x] Add hover indent effect (15px right shift on selected item)
- [x] Add animated orange line separators between settings items with same pulsing/sweep effect as main menu

### Task 3 - Handle settings-specific value displays

**Files:**
- Modify: `game.py` (draw_options_menu method)

- [x] Display resolution and fullscreen values inline with their labels using consistent styling
- [x] Selected values highlighted in cyan/orange, unselected in gray
- [x] Ensure "Back" item styled identically to main menu items

## Validation

- [ ] Manual test: open settings menu, verify fractal background visible, items styled like main menu
- [ ] Manual test: hover/select items, verify indent animation and color changes match main menu
- [ ] Manual test: change resolution and fullscreen, verify values display correctly
- [ ] Manual test: return to main menu, verify transition is smooth

## Wrap-up

- [ ] move this plan to `docs/plans/completed/`
