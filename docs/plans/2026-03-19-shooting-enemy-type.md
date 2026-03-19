# Add Shooting Enemy Type

Add a "shooter" enemy type that fires projectiles at the player from a distance. The shooter maintains distance from the player (~200px) instead of rushing in, and fires slow, dodgeable projectiles. This forces the player to stay mobile and actively dodge, rather than sitting in one spot.

## Overview

- **Files involved:** `game.py`
- **Related patterns:** existing `Bullet` class, `ENEMY_TYPES` dict, `WAVE_COMPOSITION`, `Enemy` class update/draw methods, main game loop bullet update and collision sections
- **Dependencies:** none (pygame only)

## Design Decisions

- Shooter keeps distance: moves away if player is too close, approaches if too far
- Fires slow projectiles (speed ~4, half of player bullet speed 8) so player can dodge
- Enemy projectiles stored in a separate list (`enemy_bullets`) to keep collision logic clean
- Enemy bullets visually distinct: red/orange color, slightly larger than player bullets
- Enemy bullets damage player on contact, blocked by obstacles
- Shooter appears starting wave 8, frequency increases in later waves
- Moderate stats: 5 HP, 0.8 speed, radius 13, diamond shape, 5 XP

## Approach

- **Testing approach:** Manual testing (pygame game with no test framework)
- Complete each task fully before moving to the next

## Task 1 - Add shooter enemy type definition and spawning

**Files:**
- Modify: `game.py`

- [ ] Add "shooter" entry to `ENEMY_TYPES` dict with hp=5, speed=0.8, radius=13, color=(255,100,50), xp_value=5
- [ ] Add shooter to `WAVE_COMPOSITION` starting at wave 8 with increasing weight
- [ ] Add shooter to `HEALTH_DROP_CHANCE` dict
- [ ] Manual test: verify shooters spawn in waves 8+

## Task 2 - Add enemy bullet support (EnemyBullet class and rendering)

**Files:**
- Modify: `game.py`

- [ ] Create `EnemyBullet` class (similar to `Bullet` but with slower speed ~4, larger radius ~5, red/orange color, lifetime ~120 frames)
- [ ] Add `enemy_bullets` list initialization alongside existing bullets list
- [ ] Add `EnemyBullet` update logic in game loop (movement, obstacle collision, lifetime, out-of-bounds removal)
- [ ] Add `EnemyBullet` drawing in the draw section
- [ ] Manual test: verify enemy bullets render and move correctly

## Task 3 - Implement shooter AI behavior (distance-keeping and firing)

**Files:**
- Modify: `game.py`

- [ ] Modify `Enemy.__init__` to add `shoot_cooldown` and `shoot_timer` for shooter type
- [ ] Modify `Enemy.update` to implement distance-keeping behavior for shooter: approach if >250px from player, retreat if <150px, strafe otherwise
- [ ] Add shooting logic in `Enemy.update`: when cooldown ready and player in range (~300px), fire an `EnemyBullet` toward player position
- [ ] Add unique diamond shape for shooter in `Enemy.draw`
- [ ] Manual test: verify shooters maintain distance and fire projectiles at player

## Task 4 - Add enemy bullet to player collision

**Files:**
- Modify: `game.py`

- [ ] Add collision detection between `enemy_bullets` and player in game loop (after existing bullet-enemy collision section)
- [ ] On hit: deal damage to player (1 + wave scaling similar to contact damage), remove the bullet
- [ ] Manual test: verify player takes damage from enemy projectiles, bullets are blocked by obstacles

## Task 5 - Final integration and balance testing

**Files:**
- Modify: `game.py`

- [ ] Playtest waves 1-7 to confirm no shooters appear
- [ ] Playtest waves 8-15 to verify shooter behavior, projectile dodgeability, and damage balance
- [ ] Verify shooters interact correctly with obstacles (bullets blocked, enemy pushed out)
- [ ] Verify game over, pause, and escape room still work correctly with enemy bullets active
