import pygame
import math
import random
import sys

WIDTH, HEIGHT = 1024, 768
MAP_WIDTH, MAP_HEIGHT = 4096, 3072
FPS = 60
MAX_ENEMIES = 200

# Defer pygame display/font init so the module can be imported for testing
screen = None
clock = None
font = None
title_font = None


def init_pygame():
    global screen, clock, font, title_font
    if screen is not None:
        return
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Squad Survivors")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 72)

# Game states
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_LEVEL_UP = 3

# Colors
BG = (20, 20, 30)
PLAYER_COLOR = (80, 200, 255)
ALLY_COLORS = [
    (100, 255, 100), (255, 255, 100), (255, 180, 50),
    (200, 100, 255), (255, 100, 200), (100, 255, 220),
]
ENEMY_COLOR = (255, 60, 60)
BULLET_COLOR = (255, 255, 200)
HEALTH_BG = (60, 60, 60)
HEALTH_FG = (80, 220, 80)
GRID_COLOR = (30, 30, 45)
BORDER_COLOR = (80, 80, 120)
OBSTACLE_COLOR = (90, 70, 50)
OBSTACLE_BORDER = (120, 100, 70)


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, target):
        self.x = target.x - WIDTH / 2
        self.y = target.y - HEIGHT / 2
        self.x = max(0, min(MAP_WIDTH - WIDTH, self.x))
        self.y = max(0, min(MAP_HEIGHT - HEIGHT, self.y))

    def apply(self, x, y):
        return int(x - self.x), int(y - self.y)


class Obstacle:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        pygame.draw.rect(screen, OBSTACLE_COLOR, (sx, sy, self.w, self.h))
        pygame.draw.rect(screen, OBSTACLE_BORDER, (sx, sy, self.w, self.h), 2)

    def collides_circle(self, cx, cy, radius):
        closest_x = max(self.x, min(cx, self.x + self.w))
        closest_y = max(self.y, min(cy, self.y + self.h))
        dx = cx - closest_x
        dy = cy - closest_y
        return dx * dx + dy * dy < radius * radius

    def push_circle_out(self, cx, cy, radius):
        closest_x = max(self.x, min(cx, self.x + self.w))
        closest_y = max(self.y, min(cy, self.y + self.h))
        dx = cx - closest_x
        dy = cy - closest_y
        dist_sq = dx * dx + dy * dy
        if dist_sq == 0:
            # Circle center is inside obstacle; push to nearest edge
            left = cx - self.x
            right = (self.x + self.w) - cx
            top = cy - self.y
            bottom = (self.y + self.h) - cy
            min_dist = min(left, right, top, bottom)
            if min_dist == left:
                cx = self.x - radius
            elif min_dist == right:
                cx = self.x + self.w + radius
            elif min_dist == top:
                cy = self.y - radius
            else:
                cy = self.y + self.h + radius
            return cx, cy
        if dist_sq < radius * radius:
            dist = math.sqrt(dist_sq)
            overlap = radius - dist
            cx += dx / dist * overlap
            cy += dy / dist * overlap
        return cx, cy


def generate_obstacles(count=30):
    obstacles = []
    spawn_center_x = MAP_WIDTH / 2
    spawn_center_y = MAP_HEIGHT / 2
    spawn_safe_radius = 200
    for _ in range(count):
        for _attempt in range(20):
            w = random.randint(40, 150)
            h = random.randint(40, 150)
            x = random.randint(50, MAP_WIDTH - w - 50)
            y = random.randint(50, MAP_HEIGHT - h - 50)
            cx = x + w / 2
            cy = y + h / 2
            if math.hypot(cx - spawn_center_x, cy - spawn_center_y) < spawn_safe_radius:
                continue
            overlap = False
            for o in obstacles:
                if (x < o.x + o.w + 20 and x + w + 20 > o.x and
                        y < o.y + o.h + 20 and y + h + 20 > o.y):
                    overlap = True
                    break
            if not overlap:
                obstacles.append(Obstacle(x, y, w, h))
                break
    return obstacles


def default_weapon_stats():
    """Return default weapon stats dict."""
    return {
        "damage": 1,
        "fire_rate": 25,
        "bullet_speed": 8,
        "range": 90,
        "weapon_type": "normal",
    }


class Bullet:
    SPEED = 8
    RADIUS = 4
    LIFETIME = 90  # frames

    def __init__(self, x, y, dx, dy, damage=1, speed=None, lifetime=None, weapon_type="normal"):
        self.x, self.y = x, y
        spd = speed if speed is not None else self.SPEED
        life = lifetime if lifetime is not None else self.LIFETIME
        self.damage = damage
        self.weapon_type = weapon_type
        self.pierced_enemies = set()  # track enemies already hit by piercing bullets
        length = math.hypot(dx, dy) or 1
        self.vx = dx / length * spd
        self.vy = dy / length * spd
        self.life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        pygame.draw.circle(screen, BULLET_COLOR, (sx, sy), self.RADIUS)


class Unit:
    RADIUS = 14
    SPEED = 2.5
    SHOOT_COOLDOWN = 25

    ALLY_LIFETIME = 600  # frames (~10 seconds)

    def __init__(self, x, y, color, is_player=False):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.is_player = is_player
        self.cooldown = 0
        self.hp = 5 if is_player else 3
        self.lifetime = -1 if is_player else self.ALLY_LIFETIME

    def move_towards(self, tx, ty, allies, obstacles=()):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 3:
            return
        nx, ny = dx / dist * self.SPEED, dy / dist * self.SPEED
        new_x, new_y = self.x + nx, self.y + ny
        # Separation from allies
        for a in allies:
            if a is self:
                continue
            adx, ady = new_x - a.x, new_y - a.y
            adist = math.hypot(adx, ady)
            if adist < self.RADIUS * 2.5 and adist > 0:
                push = (self.RADIUS * 2.5 - adist) * 0.3
                new_x += adx / adist * push
                new_y += ady / adist * push
        self.x = max(self.RADIUS, min(MAP_WIDTH - self.RADIUS, new_x))
        self.y = max(self.RADIUS, min(MAP_HEIGHT - self.RADIUS, new_y))
        for obs in obstacles:
            self.x, self.y = obs.push_circle_out(self.x, self.y, self.RADIUS)

    def shoot_at(self, target, bullets, weapon_stats=None):
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        fire_rate = weapon_stats["fire_rate"] if weapon_stats else self.SHOOT_COOLDOWN
        bullet_speed = weapon_stats["bullet_speed"] if weapon_stats else Bullet.SPEED
        bullet_range = weapon_stats["range"] if weapon_stats else Bullet.LIFETIME
        damage = weapon_stats["damage"] if weapon_stats else 1
        weapon_type = weapon_stats["weapon_type"] if weapon_stats else "normal"
        dx, dy = target.x - self.x, target.y - self.y
        shoot_dist = bullet_range * bullet_speed  # max distance bullets can travel
        if math.hypot(dx, dy) < shoot_dist:
            if weapon_type == "shotgun":
                # Fire 5 bullets in a spread, each with reduced damage
                base_angle = math.atan2(dy, dx)
                spread_angle = math.radians(30)  # total spread
                shotgun_damage = max(1, damage // 2)
                for i in range(5):
                    angle = base_angle + spread_angle * (i - 2) / 2
                    sdx = math.cos(angle)
                    sdy = math.sin(angle)
                    bullets.append(Bullet(self.x, self.y, sdx, sdy,
                                          damage=shotgun_damage, speed=bullet_speed,
                                          lifetime=bullet_range, weapon_type="shotgun"))
            else:
                bullets.append(Bullet(self.x, self.y, dx, dy,
                                      damage=damage, speed=bullet_speed,
                                      lifetime=bullet_range, weapon_type=weapon_type))
            self.cooldown = fire_rate

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        # Fade ally color based on remaining lifetime
        draw_color = self.color
        if not self.is_player and self.lifetime >= 0:
            fade = max(0.2, self.lifetime / self.ALLY_LIFETIME)
            draw_color = tuple(int(c * fade) for c in self.color)
        pygame.draw.circle(screen, draw_color, (sx, sy), self.RADIUS)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), self.RADIUS, 2)
        # HP bar
        bar_w = self.RADIUS * 2
        max_hp = 5 if self.is_player else 3
        filled = bar_w * max(0, self.hp) / max_hp
        bx = sx - bar_w // 2
        by = sy - self.RADIUS - 8
        pygame.draw.rect(screen, HEALTH_BG, (bx, by, bar_w, 4))
        pygame.draw.rect(screen, HEALTH_FG, (bx, by, int(filled), 4))
        # Lifetime bar for allies
        if not self.is_player and self.lifetime >= 0:
            life_filled = bar_w * self.lifetime / self.ALLY_LIFETIME
            by2 = sy - self.RADIUS - 13
            pygame.draw.rect(screen, HEALTH_BG, (bx, by2, bar_w, 3))
            pygame.draw.rect(screen, (100, 180, 255), (bx, by2, int(life_filled), 3))


class Enemy:
    RADIUS = 12
    SPEED = 1.2
    _next_id = 0

    def __init__(self, camera):
        Enemy._next_id += 1
        self.uid = Enemy._next_id
        # Spawn at edges of camera view
        cam_left = camera.x
        cam_top = camera.y
        cam_right = camera.x + WIDTH
        cam_bottom = camera.y + HEIGHT
        margin = 60
        side = random.randint(0, 3)
        if side == 0:  # top
            self.x = random.uniform(cam_left - margin, cam_right + margin)
            self.y = cam_top - margin
        elif side == 1:  # bottom
            self.x = random.uniform(cam_left - margin, cam_right + margin)
            self.y = cam_bottom + margin
        elif side == 2:  # left
            self.x = cam_left - margin
            self.y = random.uniform(cam_top - margin, cam_bottom + margin)
        else:  # right
            self.x = cam_right + margin
            self.y = random.uniform(cam_top - margin, cam_bottom + margin)
        # Clamp to map bounds (with some allowance outside)
        self.x = max(-margin, min(MAP_WIDTH + margin, float(self.x)))
        self.y = max(-margin, min(MAP_HEIGHT + margin, float(self.y)))
        self.hp = 2

    def update(self, target):
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1
        self.x += dx / dist * self.SPEED
        self.y += dy / dist * self.SPEED

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        r = self.RADIUS
        points = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame.draw.polygon(screen, ENEMY_COLOR, points)
        pygame.draw.polygon(screen, (200, 40, 40), points, 2)


def generate_xp_thresholds(max_level=50):
    """Generate XP thresholds for each level. Level n requires thresholds[n-1] XP."""
    thresholds = []
    for i in range(max_level):
        thresholds.append(10 + i * 5 + i * i * 2)
    return thresholds


def check_level_up(xp, level, thresholds):
    """Check if xp >= threshold for current level. Returns (new_xp, new_level, leveled_up)."""
    if level - 1 >= len(thresholds):
        return xp, level, False
    threshold = thresholds[level - 1]
    if xp >= threshold:
        return xp - threshold, level + 1, True
    return xp, level, False


STAT_UPGRADES = [
    {"name": "+Damage", "stat": "damage", "amount": 1},
    {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3},
    {"name": "+Bullet Speed", "stat": "bullet_speed", "amount": 2},
    {"name": "+Range", "stat": "range", "amount": 15},
]

WEAPON_TYPES = ["shotgun", "piercing", "explosive"]


def generate_upgrade_options(level, weapon_stats):
    """Generate 3 upgrade options. At milestone levels (5,10,15...), one is a weapon type."""
    options = random.sample(STAT_UPGRADES, min(3, len(STAT_UPGRADES)))
    options = [dict(o) for o in options]  # copy
    is_milestone = level % 5 == 0
    if is_milestone:
        available_weapons = [w for w in WEAPON_TYPES if w != weapon_stats.get("weapon_type")]
        if available_weapons:
            weapon = random.choice(available_weapons)
            options[random.randint(0, len(options) - 1)] = {
                "name": f"Weapon: {weapon.title()}",
                "weapon_type": weapon,
            }
    return options


def apply_upgrade(weapon_stats, option):
    """Apply an upgrade option to weapon stats. Returns updated stats."""
    if "weapon_type" in option:
        weapon_stats["weapon_type"] = option["weapon_type"]
    else:
        weapon_stats[option["stat"]] += option["amount"]
        # Clamp fire_rate to minimum of 3
        if option["stat"] == "fire_rate":
            weapon_stats["fire_rate"] = max(3, weapon_stats["fire_rate"])
    return weapon_stats


def find_closest_enemy(unit, enemies):
    best, best_d = None, float('inf')
    for e in enemies:
        d = math.hypot(e.x - unit.x, e.y - unit.y)
        if d < best_d:
            best, best_d = e, d
    return best


def draw_grid(camera):
    grid_size = 128
    # Calculate visible grid lines
    start_x = int(camera.x // grid_size) * grid_size
    start_y = int(camera.y // grid_size) * grid_size
    for x in range(start_x, int(camera.x + WIDTH) + grid_size, grid_size):
        if 0 <= x <= MAP_WIDTH:
            sx = int(x - camera.x)
            pygame.draw.line(screen, GRID_COLOR, (sx, 0), (sx, HEIGHT))
    for y in range(start_y, int(camera.y + HEIGHT) + grid_size, grid_size):
        if 0 <= y <= MAP_HEIGHT:
            sy = int(y - camera.y)
            pygame.draw.line(screen, GRID_COLOR, (0, sy), (WIDTH, sy))
    # Draw map border
    bx, by = camera.apply(0, 0)
    bw, bh = MAP_WIDTH, MAP_HEIGHT
    pygame.draw.rect(screen, BORDER_COLOR, (bx, by, bw, bh), 3)


def draw_menu():
    screen.fill(BG)
    title = title_font.render("Squad Survivors", True, PLAYER_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))
    prompt = font.render("Press ENTER to Start", True, (200, 200, 200))
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 40))
    pygame.display.flip()


def draw_game_over(score, level=1):
    screen.fill(BG)
    t1 = title_font.render("GAME OVER", True, (255, 100, 100))
    screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, HEIGHT // 3))
    t2 = font.render(f"Score: {score}   Level: {level}", True, (220, 220, 220))
    screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 + 20))
    t3 = font.render("Press ENTER to Restart", True, (200, 200, 200))
    screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, HEIGHT // 2 + 60))
    pygame.display.flip()


def run():
    init_pygame()
    state = STATE_MENU
    camera = Camera()
    player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
    obstacles = []
    allies = []
    enemies = []
    bullets = []
    score = 0
    spawn_timer = 0
    spawn_interval = 90  # frames between spawns
    wave = 1
    wave_timer = 0
    xp = 0
    level = 1
    xp_thresholds = generate_xp_thresholds()
    weapon_stats = default_weapon_stats()
    upgrade_options = []

    def reset_game():
        nonlocal camera, player, obstacles, allies, enemies, bullets, score
        nonlocal spawn_timer, spawn_interval, wave, wave_timer
        nonlocal xp, level, weapon_stats, upgrade_options
        camera = Camera()
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        obstacles = generate_obstacles()
        allies = []
        enemies = []
        bullets = []
        score = 0
        spawn_timer = 0
        spawn_interval = 90
        wave = 1
        wave_timer = 0
        xp = 0
        level = 1
        weapon_stats = default_weapon_stats()
        upgrade_options = []

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == STATE_PLAYING:
                        state = STATE_MENU
                    elif state == STATE_GAME_OVER:
                        state = STATE_MENU
                    elif state == STATE_LEVEL_UP:
                        state = STATE_MENU
                    elif state == STATE_MENU:
                        running = False
                elif state == STATE_LEVEL_UP and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(upgrade_options):
                        apply_upgrade(weapon_stats, upgrade_options[idx])
                        upgrade_options = []
                        state = STATE_PLAYING
                elif event.key == pygame.K_RETURN:
                    if state == STATE_MENU:
                        reset_game()
                        state = STATE_PLAYING
                    elif state == STATE_GAME_OVER:
                        reset_game()
                        state = STATE_PLAYING

        if state == STATE_MENU:
            draw_menu()
            clock.tick(FPS)
            continue

        if state == STATE_GAME_OVER:
            draw_game_over(score, level)
            clock.tick(FPS)
            continue

        if state == STATE_LEVEL_UP:
            screen.fill(BG)
            title = title_font.render(f"Level {level}!", True, (255, 220, 100))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))
            subtitle = font.render("Choose an upgrade:", True, (200, 200, 200))
            screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT // 4 + 70))
            for i, opt in enumerate(upgrade_options):
                color = (180, 255, 180) if "weapon_type" in opt else (220, 220, 255)
                text = font.render(f"[{i+1}] {opt['name']}", True, color)
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 + i * 50))
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # Input
        keys = pygame.key.get_pressed()
        mx, my = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            my -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            my += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += 1
        if mx or my:
            length = math.hypot(mx, my)
            player.x += mx / length * 3.5
            player.y += my / length * 3.5
            player.x = max(player.RADIUS, min(MAP_WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(MAP_HEIGHT - player.RADIUS, player.y))
            for obs in obstacles:
                player.x, player.y = obs.push_circle_out(player.x, player.y, player.RADIUS)

        # Update camera
        camera.update(player)

        # Spawn enemies
        spawn_timer += 1
        wave_timer += 1
        if wave_timer > 480:
            wave += 1
            wave_timer = 0
            spawn_interval = max(10, spawn_interval - 14)
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            for _ in range(wave + wave // 2):
                if len(enemies) >= MAX_ENEMIES:
                    break
                enemies.append(Enemy(camera))

        # Tick ally lifetimes and remove expired allies
        for a in allies:
            if a.lifetime > 0:
                a.lifetime -= 1
        allies = [a for a in allies if a.lifetime != 0]

        # Allies follow player loosely
        squad = [player] + allies
        for i, a in enumerate(allies):
            # Orbit around player
            angle = (2 * math.pi * i) / max(len(allies), 1)
            orbit_r = 50 + len(allies) * 5
            tx = player.x + math.cos(angle) * orbit_r
            ty = player.y + math.sin(angle) * orbit_r
            a.move_towards(tx, ty, squad, obstacles)

        # Shooting — player and allies shoot at closest enemy
        for u in squad:
            target = find_closest_enemy(u, enemies)
            if target:
                ws = weapon_stats if u.is_player else None
                u.shoot_at(target, bullets, weapon_stats=ws)

        # Update bullets
        for b in bullets:
            b.update()
        for b in bullets:
            for obs in obstacles:
                if obs.collides_circle(b.x, b.y, b.RADIUS):
                    b.life = 0
                    break
        bullets = [b for b in bullets if b.life > 0 and
                   -50 <= b.x <= MAP_WIDTH + 50 and -50 <= b.y <= MAP_HEIGHT + 50]

        # Bullet-enemy collision
        new_enemies = []
        killed = 0
        explosive_hits = []  # (x, y, damage, direct_hit_uid) for area damage
        for e in enemies:
            hit = False
            for b in bullets:
                if b.life <= 0:
                    continue
                if e.uid in b.pierced_enemies:
                    continue
                if math.hypot(b.x - e.x, b.y - e.y) < e.RADIUS + b.RADIUS:
                    e.hp -= b.damage
                    if b.weapon_type == "piercing":
                        b.pierced_enemies.add(e.uid)
                    elif b.weapon_type == "explosive":
                        explosive_hits.append((b.x, b.y, b.damage, e.uid))
                        b.life = 0
                    else:
                        b.life = 0
                    if e.hp <= 0:
                        hit = True
                        killed += 1
                    break
            if not hit:
                new_enemies.append(e)
        enemies = new_enemies

        # Explosive area damage (skip enemies already hit directly by the bullet)
        EXPLOSIVE_RADIUS = 60
        for ex, ey, edmg, direct_hit_uid in explosive_hits:
            surviving_after_explosion = []
            for e in enemies:
                if e.uid != direct_hit_uid and math.hypot(e.x - ex, e.y - ey) < EXPLOSIVE_RADIUS:
                    e.hp -= edmg
                    if e.hp <= 0:
                        killed += 1
                        continue
                surviving_after_explosion.append(e)
            enemies = surviving_after_explosion
        score += killed

        # Award XP and check level-up
        xp += killed
        xp, level, leveled_up = check_level_up(xp, level, xp_thresholds)
        if leveled_up:
            upgrade_options = generate_upgrade_options(level, weapon_stats)
            state = STATE_LEVEL_UP
            # Spawn allies before pausing (reward kills even on level-up frame)
            for _ in range(killed):
                if random.random() < 0.1:
                    color = random.choice(ALLY_COLORS)
                    a = Unit(player.x + random.uniform(-30, 30),
                             player.y + random.uniform(-30, 30), color)
                    allies.append(a)
            # Skip enemy movement and collision to prevent death during level-up
            clock.tick(FPS)
            continue

        # Spawn allies for kills (1-in-10 chance per kill)
        for _ in range(killed):
            if random.random() < 0.1:
                color = random.choice(ALLY_COLORS)
                a = Unit(player.x + random.uniform(-30, 30),
                         player.y + random.uniform(-30, 30), color)
                allies.append(a)

        # Update enemies
        for e in enemies:
            e.update(player)
            for obs in obstacles:
                e.x, e.y = obs.push_circle_out(e.x, e.y, e.RADIUS)

        # Enemy-player collision (damage player)
        surviving = []
        for e in enemies:
            if math.hypot(e.x - player.x, e.y - player.y) < e.RADIUS + player.RADIUS:
                player.hp -= 1
            else:
                surviving.append(e)
        enemies = surviving

        if player.hp <= 0:
            state = STATE_GAME_OVER

        # Draw
        screen.fill(BG)
        draw_grid(camera)
        for obs in obstacles:
            obs.draw(camera)
        for b in bullets:
            b.draw(camera)
        for e in enemies:
            e.draw(camera)
        for a in allies:
            a.draw(camera)
        player.draw(camera)

        # HUD
        hud = font.render(f"Score: {score}   Squad: {1 + len(allies)}   Wave: {wave}   Lv: {level}   Weapon: {weapon_stats['weapon_type']}", True, (220, 220, 220))
        screen.blit(hud, (10, 10))

        # XP bar
        xp_bar_w = 200
        xp_bar_h = 8
        xp_bar_x = 10
        xp_bar_y = 42
        current_threshold = xp_thresholds[level - 1] if level - 1 < len(xp_thresholds) else 1
        xp_fill = min(xp_bar_w, int(xp_bar_w * xp / current_threshold))
        pygame.draw.rect(screen, HEALTH_BG, (xp_bar_x, xp_bar_y, xp_bar_w, xp_bar_h))
        pygame.draw.rect(screen, (180, 120, 255), (xp_bar_x, xp_bar_y, xp_fill, xp_bar_h))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
