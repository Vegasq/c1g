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
BG = (5, 5, 15)
PLAYER_COLOR = (0, 220, 255)
ALLY_COLORS = [
    (0, 150, 255), (100, 80, 255), (180, 0, 255),
    (255, 0, 200), (0, 200, 220), (120, 100, 255),
]
ENEMY_COLOR = (255, 30, 60)
BULLET_COLOR = (200, 255, 255)
HEALTH_BG = (60, 60, 60)
HEALTH_FG = (0, 255, 180)
GRID_COLOR = (15, 15, 40)
BORDER_COLOR = (150, 0, 255)
OBSTACLE_COLOR = (15, 10, 30)
OBSTACLE_BORDER = (120, 0, 200)
HEALTH_PICKUP_COLOR = (0, 255, 100)


_glow_surface_cache = {}

CULL_MARGIN = 80  # extra pixels beyond screen edge before culling


def _is_visible(camera, x, y, margin=CULL_MARGIN):
    """Return True if world-space (x, y) is within the visible screen area."""
    return (-margin <= x - camera.x <= WIDTH + margin and
            -margin <= y - camera.y <= HEIGHT + margin)


def _is_rect_visible(camera, x, y, w, h, margin=CULL_MARGIN):
    """Return True if a world-space rect overlaps the visible screen area."""
    return (x + w + margin >= camera.x and x - margin <= camera.x + WIDTH and
            y + h + margin >= camera.y and y - margin <= camera.y + HEIGHT)


def _get_glow_surface(size):
    """Return a cached SRCALPHA surface of the given (w, h) size."""
    surf = _glow_surface_cache.get(size)
    if surf is None:
        if len(_glow_surface_cache) > 256:
            _glow_surface_cache.clear()
        surf = pygame.Surface(size, pygame.SRCALPHA)
        _glow_surface_cache[size] = surf
    return surf


def draw_glow(surface, color, center, radius, intensity=80, layers=4):
    """Draw layered transparent circles to simulate neon glow."""
    if radius <= 0 or layers <= 0:
        return
    for i in range(layers, 0, -1):
        layer_radius = int(radius * (1 + i * 0.5))
        dim = layer_radius * 2
        glow_surf = _get_glow_surface((dim, dim))
        glow_surf.fill((0, 0, 0, 0))
        alpha = max(10, intensity // i)
        glow_color = (color[0], color[1], color[2], alpha)
        pygame.draw.circle(glow_surf, glow_color, (layer_radius, layer_radius), layer_radius)
        surface.blit(glow_surf, (center[0] - layer_radius, center[1] - layer_radius))


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
        # Rectangular glow layers matching obstacle shape
        for i in range(3, 0, -1):
            pad = i * 4
            alpha = max(10, 50 // i)
            dim = (self.w + pad * 2, self.h + pad * 2)
            glow_surf = _get_glow_surface(dim)
            glow_surf.fill((0, 0, 0, 0))
            glow_color = (OBSTACLE_BORDER[0], OBSTACLE_BORDER[1], OBSTACLE_BORDER[2], alpha)
            pygame.draw.rect(glow_surf, glow_color, (0, 0, dim[0], dim[1]))
            screen.blit(glow_surf, (sx - pad, sy - pad))
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
        draw_glow(screen, BULLET_COLOR, (sx, sy), self.RADIUS, intensity=60, layers=3)
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
        self.max_hp = 5 if is_player else 3
        self.hp = self.max_hp
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
        draw_glow(screen, draw_color, (sx, sy), self.RADIUS, intensity=80, layers=4)
        pygame.draw.circle(screen, draw_color, (sx, sy), self.RADIUS)
        outline = tuple(min(255, c + 60) for c in draw_color)
        pygame.draw.circle(screen, outline, (sx, sy), self.RADIUS, 2)
        # HP bar
        bar_w = self.RADIUS * 2
        max_hp = self.max_hp
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


ENEMY_TYPES = {
    "basic": {"hp": 2, "speed": 1.2, "radius": 12, "color": (255, 30, 60), "xp_value": 1},
    "runner": {"hp": 1, "speed": 2.2, "radius": 8, "color": (230, 255, 0), "xp_value": 1},
    "brute": {"hp": 6, "speed": 0.7, "radius": 18, "color": (255, 140, 0), "xp_value": 3},
    "shielded": {"hp": 4, "speed": 1.0, "radius": 14, "color": (0, 255, 255), "xp_value": 4, "shield": True},
    "splitter": {"hp": 3, "speed": 1.0, "radius": 14, "color": (0, 255, 100), "xp_value": 2},
    "mini": {"hp": 1, "speed": 1.8, "radius": 7, "color": (0, 255, 100), "xp_value": 1},
    "elite": {"hp": 10, "speed": 1.8, "radius": 16, "color": (255, 0, 255), "xp_value": 8},
}

# Wave-based spawn weight tables: maps wave thresholds to enemy type weights.
# Checked in descending order; first matching threshold is used.
WAVE_COMPOSITION = [
    (12, {"runner": 10, "brute": 10, "shielded": 30, "splitter": 30, "elite": 20}),
    (10, {"runner": 20, "brute": 20, "shielded": 25, "splitter": 25, "elite": 10}),
    (8, {"runner": 25, "brute": 25, "shielded": 25, "splitter": 25}),
    (6, {"basic": 30, "runner": 25, "brute": 20, "shielded": 15, "splitter": 10}),
    (3, {"basic": 60, "runner": 25, "brute": 15}),
    (1, {"basic": 100}),
]


def get_enemy_type_for_wave(wave):
    """Select a random enemy type based on the current wave's weight table."""
    for threshold, weights in WAVE_COMPOSITION:
        if wave >= threshold:
            types = list(weights.keys())
            cumulative = list(weights.values())
            return random.choices(types, weights=cumulative, k=1)[0]
    return "basic"


class Enemy:
    _next_id = 0

    def __init__(self, camera, enemy_type="basic"):
        Enemy._next_id += 1
        self.uid = Enemy._next_id
        self.enemy_type = enemy_type
        type_cfg = ENEMY_TYPES[enemy_type]
        self.hp = type_cfg["hp"]
        self.speed = type_cfg["speed"]
        self.radius = type_cfg["radius"]
        self.color = type_cfg["color"]
        self.xp_value = type_cfg["xp_value"]
        self.shield = type_cfg.get("shield", False)
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

    def update(self, target):
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1
        self.x += dx / dist * self.speed
        self.y += dy / dist * self.speed

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        r = self.radius
        draw_glow(screen, self.color, (sx, sy), r, intensity=80, layers=4)
        if self.enemy_type == "runner":
            points = [(sx, sy - r), (sx + r, sy + r), (sx - r, sy + r)]
        elif self.enemy_type == "brute":
            points = [
                (sx + r * math.cos(math.radians(60 * i - 90)),
                 sy + r * math.sin(math.radians(60 * i - 90)))
                for i in range(6)
            ]
        elif self.enemy_type == "shielded":
            # Pentagon shape
            points = [
                (sx + r * math.cos(math.radians(72 * i - 90)),
                 sy + r * math.sin(math.radians(72 * i - 90)))
                for i in range(5)
            ]
        elif self.enemy_type == "elite":
            # Pulsing glow effect
            pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2  # 0..1
            extra_intensity = int(40 + 80 * pulse)
            draw_glow(screen, self.color, (sx, sy), r, intensity=extra_intensity, layers=6)
            # Octagon shape
            points = [
                (sx + r * math.cos(math.radians(45 * i)),
                 sy + r * math.sin(math.radians(45 * i)))
                for i in range(8)
            ]
        elif self.enemy_type in ("splitter", "mini"):
            # Star-like: 4-pointed star
            points = []
            for i in range(8):
                angle = math.radians(45 * i - 90)
                dist = r if i % 2 == 0 else r * 0.5
                points.append((sx + dist * math.cos(angle), sy + dist * math.sin(angle)))
        else:
            points = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame.draw.polygon(screen, self.color, points)
        enemy_outline = tuple(min(255, c + 60) for c in self.color)
        pygame.draw.polygon(screen, enemy_outline, points, 2)
        # Draw shield ring if active
        if self.shield:
            shield_color = (100, 255, 255)
            pygame.draw.circle(screen, shield_color, (sx, sy), r + 4, 2)


class HealthPickup:
    RADIUS = 8
    LIFETIME = 600  # frames (~10 seconds)
    ATTRACT_RANGE = 100
    ATTRACT_SPEED = 4.0
    COLLECT_RANGE = 20

    def __init__(self, x, y, heal_amount=1):
        self.x = float(x)
        self.y = float(y)
        self.heal_amount = heal_amount
        self.radius = self.RADIUS
        self.lifetime = self.LIFETIME
        self.collected = False

    def update(self, player):
        self.lifetime -= 1
        if self.lifetime <= 0:
            return
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.COLLECT_RANGE:
            self.collected = True
        elif dist < self.ATTRACT_RANGE and dist > 0:
            self.x += dx / dist * self.ATTRACT_SPEED
            self.y += dy / dist * self.ATTRACT_SPEED

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        fade = max(0.3, self.lifetime / self.LIFETIME)
        color = tuple(int(c * fade) for c in HEALTH_PICKUP_COLOR)
        draw_glow(screen, color, (sx, sy), self.radius, intensity=100, layers=5)
        pygame.draw.circle(screen, color, (sx, sy), self.radius)
        # Cross symbol
        cx_half = self.radius // 2
        bright = tuple(min(255, c + 80) for c in color)
        pygame.draw.line(screen, bright, (sx - cx_half, sy), (sx + cx_half, sy), 2)
        pygame.draw.line(screen, bright, (sx, sy - cx_half), (sx, sy + cx_half), 2)


HEALTH_DROP_CHANCE = {
    "basic": 0.05,
    "runner": 0.05,
    "brute": 0.12,
    "shielded": 0.08,
    "splitter": 0.06,
    "mini": 0.03,
    "elite": 0.15,
}


def get_health_drop_chance(enemy_type):
    """Return the probability of dropping a health pickup for a given enemy type."""
    return HEALTH_DROP_CHANCE.get(enemy_type, 0.05)


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


def get_scaled_amount(stat, base_amount, level):
    """Scale upgrade amounts based on player level."""
    if stat == "damage":
        if level >= 20:
            return base_amount + 2  # +3 total
        elif level >= 10:
            return base_amount + 1  # +2 total
    elif stat == "fire_rate":
        if level >= 15:
            return base_amount - 2  # -5 total
    return base_amount


def generate_upgrade_options(level, weapon_stats):
    """Generate 3 upgrade options. At milestone levels, one is a weapon type."""
    options = random.sample(STAT_UPGRADES, min(3, len(STAT_UPGRADES)))
    options = [dict(o) for o in options]  # copy
    # Scale amounts based on level
    for opt in options:
        if "stat" in opt:
            opt["amount"] = get_scaled_amount(opt["stat"], opt["amount"], level)
    milestone_interval = 4 if level > 15 else 5
    is_milestone = level % milestone_interval == 0
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
    # Brighter grid line color for subtle bloom effect
    glow_color = (25, 25, 60)
    # Calculate visible grid lines
    start_x = int(camera.x // grid_size) * grid_size
    start_y = int(camera.y // grid_size) * grid_size
    for x in range(start_x, int(camera.x + WIDTH) + grid_size, grid_size):
        if 0 <= x <= MAP_WIDTH:
            sx = int(x - camera.x)
            # Draw wider dim line for bloom, then bright center
            pygame.draw.line(screen, GRID_COLOR, (sx, 0), (sx, HEIGHT), 3)
            pygame.draw.line(screen, glow_color, (sx, 0), (sx, HEIGHT), 1)
    for y in range(start_y, int(camera.y + HEIGHT) + grid_size, grid_size):
        if 0 <= y <= MAP_HEIGHT:
            sy = int(y - camera.y)
            pygame.draw.line(screen, GRID_COLOR, (0, sy), (WIDTH, sy), 3)
            pygame.draw.line(screen, glow_color, (0, sy), (WIDTH, sy), 1)
    # Draw map border with glow
    bx, by = camera.apply(0, 0)
    bw, bh = MAP_WIDTH, MAP_HEIGHT
    pygame.draw.rect(screen, (80, 0, 140), (bx - 2, by - 2, bw + 4, bh + 4), 5)
    pygame.draw.rect(screen, BORDER_COLOR, (bx, by, bw, bh), 3)


def draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                    score, wave, level, weapon_stats, xp, xp_thresholds,
                    health_pickups=None, heal_effects=None):
    """Draw the full game scene (background, entities, HUD, XP bar)."""
    screen.fill(BG)
    draw_grid(camera)
    for obs in obstacles:
        if _is_rect_visible(camera, obs.x, obs.y, obs.w, obs.h):
            obs.draw(camera)
    for b in bullets:
        if _is_visible(camera, b.x, b.y):
            b.draw(camera)
    for e in enemies:
        if _is_visible(camera, e.x, e.y):
            e.draw(camera)
    if health_pickups:
        for hp_pickup in health_pickups:
            if _is_visible(camera, hp_pickup.x, hp_pickup.y):
                hp_pickup.draw(camera)
    if heal_effects:
        for hx, hy, ht in heal_effects:
            if _is_visible(camera, hx, hy):
                sx, sy = camera.apply(hx, hy)
                alpha_frac = ht / 15
                r = int(20 + 20 * (1 - alpha_frac))
                draw_glow(screen, HEALTH_PICKUP_COLOR, (sx, sy), r,
                          intensity=int(120 * alpha_frac), layers=3)
    for a in allies:
        if _is_visible(camera, a.x, a.y):
            a.draw(camera)
    player.draw(camera)

    # HUD
    wtype = weapon_stats['weapon_type']
    hud_text = f"Score: {score}  Squad: {1 + len(allies)}  Wave: {wave}  Lv: {level}  Weapon: {wtype}"
    hud = font.render(hud_text, True, PLAYER_COLOR)
    screen.blit(hud, (10, 10))

    # XP bar with neon glow
    xp_bar_w = 200
    xp_bar_h = 8
    xp_bar_x = 10
    xp_bar_y = 42
    current_threshold = xp_thresholds[level - 1] if level - 1 < len(xp_thresholds) else 1
    xp_fill = min(xp_bar_w, int(xp_bar_w * xp / current_threshold))
    pygame.draw.rect(screen, HEALTH_BG, (xp_bar_x, xp_bar_y, xp_bar_w, xp_bar_h))
    pygame.draw.rect(screen, BORDER_COLOR, (xp_bar_x, xp_bar_y, xp_fill, xp_bar_h))
    pygame.draw.rect(screen, BORDER_COLOR, (xp_bar_x, xp_bar_y, xp_bar_w, xp_bar_h), 1)


_dim_overlay = None


def draw_dim_overlay():
    """Draw a semi-transparent dark overlay to dim the game behind a panel."""
    global _dim_overlay
    if _dim_overlay is None:
        _dim_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _dim_overlay.fill((0, 0, 0, 153))  # ~60% opacity
    screen.blit(_dim_overlay, (0, 0))


# Upgrade panel constants
PANEL_WIDTH = 500
PANEL_HEIGHT = 350
PANEL_X = (WIDTH - PANEL_WIDTH) // 2
PANEL_Y = (HEIGHT - PANEL_HEIGHT) // 2
PANEL_BG_COLOR = (10, 5, 25, 200)
PANEL_BORDER_GLOW_LAYERS = 4
OPTION_ROW_HEIGHT = 55
OPTION_PADDING = 10
OPTION_START_Y = 90  # relative to panel top
ICON_SIZE = 32


def create_upgrade_icon(option):
    """Create a 32x32 procedural icon for an upgrade option."""
    surf = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2

    if "weapon_type" in option:
        wt = option["weapon_type"]
        if wt == "shotgun":
            # Spread pattern: three diverging lines
            color = (255, 100, 0)
            pygame.draw.line(surf, color, (4, cy), (28, 6), 2)
            pygame.draw.line(surf, color, (4, cy), (28, cy), 2)
            pygame.draw.line(surf, color, (4, cy), (28, 26), 2)
        elif wt == "piercing":
            # Arrow line going through
            color = (0, 255, 255)
            pygame.draw.line(surf, color, (4, cy), (28, cy), 2)
            pygame.draw.line(surf, color, (20, 8), (28, cy), 2)
            pygame.draw.line(surf, color, (20, 24), (28, cy), 2)
            pygame.draw.circle(surf, color, (14, cy), 3, 1)
        elif wt == "explosive":
            # Explosion circle with rays
            color = (255, 50, 50)
            pygame.draw.circle(surf, color, (cx, cy), 8, 2)
            for angle_pts in [((cx, 2), (cx, 8)), ((cx, 24), (cx, 30)),
                              ((2, cy), (8, cy)), ((24, cy), (30, cy))]:
                pygame.draw.line(surf, color, angle_pts[0], angle_pts[1], 1)
    else:
        stat = option.get("stat", "")
        if stat == "damage":
            # Sword shape
            color = (255, 80, 80)
            pygame.draw.line(surf, color, (cx, 4), (cx, 24), 3)
            pygame.draw.line(surf, color, (cx - 8, 18), (cx + 8, 18), 2)
            pygame.draw.rect(surf, color, (cx - 2, 24, 4, 4))
        elif stat == "fire_rate":
            # Lightning bolt
            color = (255, 255, 0)
            pygame.draw.polygon(surf, color, [
                (18, 2), (10, 14), (16, 14), (12, 30), (22, 14), (16, 14), (18, 2)
            ])
        elif stat == "bullet_speed":
            # Fast arrow
            color = (0, 200, 255)
            pygame.draw.line(surf, color, (4, cy), (26, cy), 2)
            pygame.draw.polygon(surf, color, [(26, cy - 6), (26, cy + 6), (30, cy)])
            pygame.draw.line(surf, color, (2, cy - 4), (8, cy), 1)
            pygame.draw.line(surf, color, (2, cy + 4), (8, cy), 1)
        elif stat == "range":
            # Crosshair
            color = (0, 255, 100)
            pygame.draw.circle(surf, color, (cx, cy), 10, 1)
            pygame.draw.circle(surf, color, (cx, cy), 5, 1)
            pygame.draw.line(surf, color, (cx, 2), (cx, 30), 1)
            pygame.draw.line(surf, color, (2, cy), (30, cy), 1)

    return surf


def draw_upgrade_panel(level, upgrade_options):
    """Draw a centered floating panel with neon border for the upgrade selector."""
    # Panel background
    panel_surf = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
    panel_surf.fill(PANEL_BG_COLOR)

    # Neon glow border
    for i in range(PANEL_BORDER_GLOW_LAYERS, 0, -1):
        alpha = max(15, 80 // i)
        glow_color = (BORDER_COLOR[0], BORDER_COLOR[1], BORDER_COLOR[2], alpha)
        expand = i * 3
        glow_rect = pygame.Rect(-expand, -expand,
                                PANEL_WIDTH + expand * 2, PANEL_HEIGHT + expand * 2)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=8)
        screen.blit(glow_surf, (PANEL_X - expand, PANEL_Y - expand))

    # Solid border
    pygame.draw.rect(panel_surf, BORDER_COLOR,
                     pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT), 2, border_radius=6)

    # Title
    title = title_font.render(f"Level {level}!", True, BORDER_COLOR)
    title_glow = title_font.render(f"Level {level}!", True, (80, 0, 140))
    tx = PANEL_WIDTH // 2 - title.get_width() // 2
    ty = 15
    panel_surf.blit(title_glow, (tx - 2, ty - 2))
    panel_surf.blit(title_glow, (tx + 2, ty + 2))
    panel_surf.blit(title, (tx, ty))

    # Subtitle
    subtitle = font.render("Choose an upgrade:", True, (0, 180, 220))
    panel_surf.blit(subtitle, (PANEL_WIDTH // 2 - subtitle.get_width() // 2, 60))

    # Upgrade option rows
    mouse_x, mouse_y = pygame.mouse.get_pos()
    hovered_idx = get_hovered_upgrade_index(mouse_x, mouse_y, len(upgrade_options))
    for i, opt in enumerate(upgrade_options):
        row_y = OPTION_START_Y + i * OPTION_ROW_HEIGHT
        row_rect = pygame.Rect(OPTION_PADDING, row_y,
                               PANEL_WIDTH - OPTION_PADDING * 2, OPTION_ROW_HEIGHT - 5)

        hovered = (i == hovered_idx)

        # Row background
        if hovered:
            row_bg = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            row_bg.fill((BORDER_COLOR[0], BORDER_COLOR[1], BORDER_COLOR[2], 40))
            panel_surf.blit(row_bg, row_rect.topleft)
            pygame.draw.rect(panel_surf, BORDER_COLOR, row_rect, 1, border_radius=4)
        else:
            pygame.draw.rect(panel_surf, (60, 40, 100, 120), row_rect, 1, border_radius=4)

        # Icon (use cached if available)
        icon = opt.get('_icon') or create_upgrade_icon(opt)
        icon_x = OPTION_PADDING + 10
        icon_y = row_y + (OPTION_ROW_HEIGHT - 5) // 2 - ICON_SIZE // 2
        panel_surf.blit(icon, (icon_x, icon_y))

        # Option text (shifted right to make room for icon)
        color = (0, 255, 180) if "weapon_type" in opt else (100, 80, 255)
        text = font.render(f"[{i+1}] {opt['name']}", True, color)
        text_y = row_y + (OPTION_ROW_HEIGHT - 5) // 2 - text.get_height() // 2
        panel_surf.blit(text, (icon_x + ICON_SIZE + 10, text_y))

    screen.blit(panel_surf, (PANEL_X, PANEL_Y))


def get_hovered_upgrade_index(mouse_x, mouse_y, num_options):
    """Return the index of the upgrade option under the mouse, or -1 if none."""
    local_mx = mouse_x - PANEL_X
    local_my = mouse_y - PANEL_Y
    for i in range(num_options):
        row_y = OPTION_START_Y + i * OPTION_ROW_HEIGHT
        row_rect = pygame.Rect(OPTION_PADDING, row_y,
                               PANEL_WIDTH - OPTION_PADDING * 2, OPTION_ROW_HEIGHT - 5)
        if row_rect.collidepoint(local_mx, local_my):
            return i
    return -1


def draw_menu():
    screen.fill(BG)
    # Neon cyan glow behind title
    title = title_font.render("Squad Survivors", True, PLAYER_COLOR)
    title_glow = title_font.render("Squad Survivors", True, (0, 100, 140))
    tx = WIDTH // 2 - title.get_width() // 2
    ty = HEIGHT // 3
    screen.blit(title_glow, (tx - 2, ty - 2))
    screen.blit(title_glow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))
    prompt = font.render("Press ENTER to Start", True, (0, 180, 220))
    screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 40))
    pygame.display.flip()


def draw_game_over(score, level=1):
    screen.fill(BG)
    # Neon red glow on GAME OVER
    t1 = title_font.render("GAME OVER", True, ENEMY_COLOR)
    t1_glow = title_font.render("GAME OVER", True, (140, 10, 30))
    tx = WIDTH // 2 - t1.get_width() // 2
    ty = HEIGHT // 3
    screen.blit(t1_glow, (tx - 2, ty - 2))
    screen.blit(t1_glow, (tx + 2, ty + 2))
    screen.blit(t1, (tx, ty))
    t2 = font.render(f"Score: {score}   Level: {level}", True, (200, 255, 255))
    screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 + 20))
    t3 = font.render("Press ENTER to Restart", True, (0, 180, 220))
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
    health_pickups = []
    heal_effects = []
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
        nonlocal camera, player, obstacles, allies, enemies, bullets, health_pickups, heal_effects, score
        nonlocal spawn_timer, spawn_interval, wave, wave_timer
        nonlocal xp, level, weapon_stats, upgrade_options
        camera = Camera()
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        obstacles = generate_obstacles()
        allies = []
        enemies = []
        bullets = []
        health_pickups = []
        heal_effects = []
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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == STATE_LEVEL_UP and upgrade_options:
                    idx = get_hovered_upgrade_index(event.pos[0], event.pos[1], len(upgrade_options))
                    if 0 <= idx < len(upgrade_options):
                        apply_upgrade(weapon_stats, upgrade_options[idx])
                        upgrade_options = []
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
            draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                            score, wave, level, weapon_stats, xp, xp_thresholds)
            draw_dim_overlay()
            draw_upgrade_panel(level, upgrade_options)
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
            player.x = max(player.RADIUS, min(MAP_WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(MAP_HEIGHT - player.RADIUS, player.y))

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
                etype = get_enemy_type_for_wave(wave)
                enemies.append(Enemy(camera, enemy_type=etype))

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
        dead_enemies = []  # (x, y, enemy_type) for health pickup drops
        xp_earned = 0
        split_spawns = []  # (x, y) positions for mini enemies from splitters
        explosive_hits = []  # (x, y, damage, direct_hit_uid) for area damage
        for e in enemies:
            hit = False
            for b in bullets:
                if b.life <= 0:
                    continue
                if e.uid in b.pierced_enemies:
                    continue
                if math.hypot(b.x - e.x, b.y - e.y) < e.radius + b.RADIUS:
                    if e.shield:
                        # Shield absorbs first hit without dealing damage
                        e.shield = False
                        # Explosive bullets still trigger area damage even if shield absorbs direct hit
                        if b.weapon_type == "explosive":
                            explosive_hits.append((b.x, b.y, b.damage, e.uid))
                        if b.weapon_type == "piercing":
                            # Track that this piercing bullet already hit this enemy
                            b.pierced_enemies.add(e.uid)
                        else:
                            b.life = 0
                        break
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
                        xp_earned += e.xp_value
                        dead_enemies.append((e.x, e.y, e.enemy_type))
                        if e.enemy_type == "splitter":
                            split_spawns.append((e.x, e.y))
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
                    if e.shield:
                        e.shield = False
                    else:
                        e.hp -= edmg
                        if e.hp <= 0:
                            killed += 1
                            xp_earned += e.xp_value
                            dead_enemies.append((e.x, e.y, e.enemy_type))
                            if e.enemy_type == "splitter":
                                split_spawns.append((e.x, e.y))
                            continue
                surviving_after_explosion.append(e)
            enemies = surviving_after_explosion
        # Spawn mini enemies from dead splitters
        for sx, sy in split_spawns:
            for offset in (-12, 12):
                if len(enemies) >= MAX_ENEMIES:
                    break
                mini = Enemy(camera, enemy_type="mini")
                mini.x = sx + offset
                mini.y = sy
                enemies.append(mini)

        score += killed

        # Spawn health pickups from dead enemies
        for dx, dy, etype in dead_enemies:
            if random.random() < get_health_drop_chance(etype):
                health_pickups.append(HealthPickup(dx, dy))

        # Award XP and check level-up
        xp += xp_earned
        xp, level, leveled_up = check_level_up(xp, level, xp_thresholds)
        if leveled_up:
            upgrade_options = generate_upgrade_options(level, weapon_stats)
            for opt in upgrade_options:
                opt['_icon'] = create_upgrade_icon(opt)
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
                e.x, e.y = obs.push_circle_out(e.x, e.y, e.radius)

        # Enemy-player collision (damage player)
        surviving = []
        for e in enemies:
            if math.hypot(e.x - player.x, e.y - player.y) < e.radius + player.RADIUS:
                player.hp -= 1
            else:
                surviving.append(e)
        enemies = surviving

        if player.hp <= 0:
            state = STATE_GAME_OVER

        # Update health pickups
        for hp_pickup in health_pickups:
            hp_pickup.update(player)
            if hp_pickup.collected:
                player.hp = min(player.hp + hp_pickup.heal_amount, player.max_hp)
                heal_effects.append((hp_pickup.x, hp_pickup.y, 15))
        health_pickups = [hp_pickup for hp_pickup in health_pickups
                          if not hp_pickup.collected and hp_pickup.lifetime > 0]

        # Update heal effects (countdown timer)
        heal_effects = [(x, y, t - 1) for x, y, t in heal_effects if t > 0]

        # Draw
        draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                        score, wave, level, weapon_stats, xp, xp_thresholds,
                        health_pickups, heal_effects)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
