import pygame
import math
import random
import sys
import json
import os
import time

WIDTH, HEIGHT = 1024, 768
MAP_WIDTH, MAP_HEIGHT = 4096, 3072
FPS = 60
MAX_ENEMIES_BASE = 140
MAX_ENEMIES_CAP = 200


def get_max_enemies(wave):
    """Return the enemy cap for a given wave: min(200, 140 + wave * 2)."""
    return min(MAX_ENEMIES_CAP, MAX_ENEMIES_BASE + wave * 2)


def get_spawn_count(wave):
    """Return the number of enemies to spawn per spawn event."""
    return wave + wave // 4


# Defer pygame display/font init so the module can be imported for testing
screen = None
clock = None
font = None
title_font = None

# Gamepad support
JOYSTICK_DEADZONE = 0.3
GAMEPAD_NAV_REPEAT_DELAY = 0.2  # seconds between repeated D-pad/stick menu navigation
active_joystick = None
_gamepad_nav_last_time = 0  # timestamp of last gamepad menu navigation
level_up_selected_index = 0  # keyboard/gamepad selection index for upgrade panel
_last_levelup_mouse_pos = (-1, -1)  # track mouse to avoid overriding gamepad selection


def init_pygame():
    global screen, clock, font, title_font, menu_font, active_joystick, WIDTH, HEIGHT
    global options_fullscreen
    if screen is not None:
        return
    # Step 1: Initialize pygame
    pygame.init()
    # Grab the first connected joystick, if any
    try:
        if pygame.joystick.get_count() > 0:
            active_joystick = pygame.joystick.Joystick(0)
            active_joystick.init()
    except pygame.error:
        active_joystick = None
    # Step 2: Detect native display resolution
    detect_native_resolution()
    # Step 3: Load saved settings or use detected defaults
    load_settings()
    # Step 4: Create window with correct flags
    WIDTH, HEIGHT = SUPPORTED_RESOLUTIONS[options_resolution_index]
    flags = pygame.FULLSCREEN if options_fullscreen else 0
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except pygame.error:
        # Fallback to windowed mode if fullscreen fails
        options_fullscreen = False
        screen = pygame.display.set_mode((WIDTH, HEIGHT), 0)
        save_settings()
    pygame.display.set_caption("Squad Survivors")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 72)
    menu_font = pygame.font.SysFont(None, 52)


def handle_joy_device_added(current_joystick, device_index):
    """Handle JOYDEVICEADDED event. Returns the (possibly new) active joystick."""
    if current_joystick is not None:
        return current_joystick
    try:
        joy = pygame.joystick.Joystick(device_index)
        joy.init()
        return joy
    except pygame.error:
        return None


def handle_joy_device_removed(current_joystick, instance_id):
    """Handle JOYDEVICEREMOVED event. Returns the (possibly new) active joystick."""
    try:
        is_active = current_joystick is not None and instance_id == current_joystick.get_instance_id()
    except pygame.error:
        is_active = True  # Stale joystick; treat as removed
    if not is_active:
        return current_joystick
    # Active joystick was removed; try to grab another
    try:
        if pygame.joystick.get_count() > 0:
            joy = pygame.joystick.Joystick(0)
            joy.init()
            return joy
    except pygame.error:
        pass
    return None


# Game states
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_LEVEL_UP = 3
STATE_OPTIONS = 4

SUPPORTED_RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1920, 1080),
]

options_selected_index = 0  # 0=resolution, 1=fullscreen, 2=back
options_resolution_index = 1  # default 1024x768
options_fullscreen = True


def detect_native_resolution():
    """Detect native display resolution and add it to SUPPORTED_RESOLUTIONS.

    Must be called after pygame.init() but before pygame.display.set_mode().
    Returns the (width, height) tuple of the native resolution.
    Updates options_resolution_index to point to the native resolution.
    """
    global options_resolution_index
    try:
        info = pygame.display.Info()
    except pygame.error:
        return None
    native_res = (info.current_w, info.current_h)
    if native_res[0] <= 0 or native_res[1] <= 0:
        return None
    if native_res not in SUPPORTED_RESOLUTIONS:
        SUPPORTED_RESOLUTIONS.append(native_res)
        SUPPORTED_RESOLUTIONS.sort(key=lambda r: r[0] * r[1])
    options_resolution_index = SUPPORTED_RESOLUTIONS.index(native_res)
    return native_res


# Menu configuration
MENU_ITEMS = ["NEW GAME", "OPTIONS", "QUIT"]
MENU_X = 60
MENU_START_Y = 300
MENU_ITEM_HEIGHT = 60
MENU_HOVER_INDENT = 15
menu_selected_index = 0  # keyboard selection index
menu_font = None  # initialized in init_pygame
menu_fade_alpha = 0  # fade-in alpha (0-255)
menu_fade_active = True  # whether fade-in is in progress

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
HEALTH_PICKUP_COLOR = (0, 255, 180)
ESCAPE_ROOM_COLOR = (10, 25, 20)
ESCAPE_ROOM_BORDER = (0, 255, 200)


_glow_surface_cache = {}


class FractalBackground:
    """Animated neon cityscape background for the menu screen."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.buildings = self._generate_buildings()

    def _generate_buildings(self):
        buildings = []
        x = 0
        rng = random.Random(42)  # deterministic seed for consistent skyline
        while x < self.width:
            w = rng.randint(30, 80)
            h = rng.randint(80, self.height // 2 + 100)
            by = self.height - h
            # Precompute window positions for this building
            win_rng = random.Random(x * 1000 + w)
            windows = []
            for wy in range(by + 8, self.height - 8, 14):
                for wx in range(x + 4, x + w - 4, 10):
                    if win_rng.random() < 0.3:
                        flicker = win_rng.random() < 0.1
                        windows.append((wx, wy, flicker))
            buildings.append({"x": x, "w": w, "h": h, "windows": windows})
            x += w + rng.randint(2, 8)
        return buildings

    def draw(self, surface):
        surface.fill((5, 5, 15))
        ticks = pygame.time.get_ticks()
        # Slow pulse factor (0.0-1.0)
        pulse = (math.sin(ticks * 0.002) + 1.0) * 0.5
        # Color cycling offset
        cycle = ticks * 0.0005

        for b in self.buildings:
            bx, bw, bh = b["x"], b["w"], b["h"]
            by = self.height - bh

            # Dark building body
            pygame.draw.rect(surface, (8, 8, 20), (bx, by, bw, bh))

            # Neon edge color: cycle between cyan, purple, red
            r = int(80 + 60 * math.sin(cycle + bx * 0.01))
            g = int(20 + 30 * math.sin(cycle + bx * 0.01 + 2.0))
            bl = int(120 + 80 * math.sin(cycle + bx * 0.01 + 4.0))
            edge_color = (max(0, min(255, r)),
                          max(0, min(255, g)),
                          max(0, min(255, bl)))

            # Glowing edges
            pygame.draw.rect(surface, edge_color, (bx, by, bw, bh), 1)

            # Animated scanline effect (horizontal lines moving down)
            scanline_offset = (ticks // 30) % 6
            line_color = (edge_color[0] // 4, edge_color[1] // 4, edge_color[2] // 4)
            for sy in range(scanline_offset, bh, 6):
                pygame.draw.line(surface, line_color,
                                 (bx + 1, by + sy), (bx + bw - 2, by + sy))

            # Precomputed lit windows
            for wx, wy, flicker in b["windows"]:
                brightness = 0.5 + 0.5 * pulse if flicker else 0.3
                wc = (int(edge_color[0] * brightness),
                      int(edge_color[1] * brightness),
                      int(edge_color[2] * brightness))
                pygame.draw.rect(surface, wc, (wx, wy, 4, 4))


_menu_background = None
_fade_overlay = None


def _reset_menu_state():
    """Reset menu selection and fade-in state for transitions back to menu."""
    global menu_selected_index, menu_fade_alpha, menu_fade_active
    menu_fade_alpha = 0
    menu_fade_active = True
    try:
        mx, my = pygame.mouse.get_pos()
        idx = get_hovered_menu_index(mx, my)
        menu_selected_index = idx if idx >= 0 else 0
    except pygame.error:
        menu_selected_index = 0


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


class EscapeRoom:
    def __init__(self, x, y, w=120, h=120):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.pulse_timer = 0

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        sw = WIDTH
        sh = HEIGHT
        # pulse_timer is incremented in draw_game_scene every frame
        if (sx + self.w < -CULL_MARGIN or sx > sw + CULL_MARGIN or
                sy + self.h < -CULL_MARGIN or sy > sh + CULL_MARGIN):
            return
        pulse = 0.6 + 0.4 * math.sin(self.pulse_timer * 0.05)
        # Glow layers
        for i in range(4, 0, -1):
            pad = i * 6
            alpha = max(10, int(60 * pulse) // i)
            dim = (self.w + pad * 2, self.h + pad * 2)
            glow_surf = _get_glow_surface(dim)
            glow_surf.fill((0, 0, 0, 0))
            glow_color = (ESCAPE_ROOM_BORDER[0], ESCAPE_ROOM_BORDER[1],
                          ESCAPE_ROOM_BORDER[2], alpha)
            pygame.draw.rect(glow_surf, glow_color, (0, 0, dim[0], dim[1]))
            screen.blit(glow_surf, (sx - pad, sy - pad))
        pygame.draw.rect(screen, ESCAPE_ROOM_COLOR, (sx, sy, self.w, self.h))
        border_col = tuple(int(c * pulse) for c in ESCAPE_ROOM_BORDER)
        pygame.draw.rect(screen, border_col, (sx, sy, self.w, self.h), 3)

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

    def relocate(self, obstacles, escape_rooms=None):
        spawn_center_x = MAP_WIDTH / 2
        spawn_center_y = MAP_HEIGHT / 2
        spawn_safe_radius = 200
        if escape_rooms is None:
            escape_rooms = []
        for _attempt in range(50):
            x = random.randint(50, MAP_WIDTH - self.w - 50)
            y = random.randint(50, MAP_HEIGHT - self.h - 50)
            cx = x + self.w / 2
            cy = y + self.h / 2
            if math.hypot(cx - spawn_center_x, cy - spawn_center_y) < spawn_safe_radius:
                continue
            overlap = False
            for o in obstacles:
                if (x < o.x + o.w + 20 and x + self.w + 20 > o.x and
                        y < o.y + o.h + 20 and y + self.h + 20 > o.y):
                    overlap = True
                    break
            if not overlap:
                for er in escape_rooms:
                    if er is self:
                        continue
                    if (x < er.x + er.w + 20 and x + self.w + 20 > er.x and
                            y < er.y + er.h + 20 and y + self.h + 20 > er.y):
                        overlap = True
                        break
            if not overlap:
                self.x = x
                self.y = y
                return
        # Fallback: relaxed placement (skip obstacle check, keep spawn-safe)
        for _attempt in range(50):
            x = random.randint(50, MAP_WIDTH - self.w - 50)
            y = random.randint(50, MAP_HEIGHT - self.h - 50)
            cx = x + self.w / 2
            cy = y + self.h / 2
            if math.hypot(cx - spawn_center_x, cy - spawn_center_y) >= spawn_safe_radius:
                self.x = x
                self.y = y
                return
        self.x = random.randint(50, MAP_WIDTH - self.w - 50)
        self.y = random.randint(50, MAP_HEIGHT - self.h - 50)


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
        "cooldown": 0,
    }


def default_weapon_inventory():
    """Return a weapon inventory list containing one normal weapon."""
    return [default_weapon_stats()]


STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def default_run_stats():
    """Return default per-run tracking stats."""
    return {
        "damage_dealt": 0,
        "damage_taken": 0,
        "weapons_used": set(),
        "weapon_damage": {},
        "weapon_kills": {},
        "weapon_picks": {},
        # Per-wave/level granular tracking for balance analysis
        "wave_logs": [],
        "level_logs": [],
        "wave_damage_dealt": 0,
        "wave_damage_taken": 0,
        "wave_kills": 0,
        "wave_xp_earned": 0,
    }


def snapshot_weapon_power(weapon_inventory):
    """Snapshot current weapon stats for logging."""
    return [{"type": w["weapon_type"], "dmg": w["damage"], "fire_rate": w["fire_rate"],
             "speed": w["bullet_speed"], "range": w["range"]} for w in weapon_inventory]


def collect_run_stats(run_stats, score, level, wave, xp_earned_total, survival_time, weapon_inventory):
    """Gather per-run data into a serializable dict."""
    final_weapons = [w["weapon_type"] for w in weapon_inventory]
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kills": score,
        "damage_dealt": run_stats["damage_dealt"],
        "damage_taken": run_stats["damage_taken"],
        "waves_reached": wave,
        "level_reached": level,
        "survival_time_seconds": round(survival_time, 1),
        "weapons_used": list(run_stats["weapons_used"]),
        "xp_earned": xp_earned_total,
        "final_weapons": final_weapons,
        "weapon_stats": collect_weapon_stats(run_stats),
        "wave_logs": run_stats["wave_logs"],
        "level_logs": run_stats["level_logs"],
    }


def collect_weapon_stats(run_stats):
    """Gather per-weapon data."""
    all_weapons = (set(run_stats["weapon_damage"].keys())
                   | set(run_stats["weapon_kills"].keys())
                   | set(run_stats["weapon_picks"].keys()))
    result = {}
    for w in all_weapons:
        result[w] = {
            "times_picked": run_stats["weapon_picks"].get(w, 0),
            "total_damage": run_stats["weapon_damage"].get(w, 0),
            "total_kills": run_stats["weapon_kills"].get(w, 0),
        }
    return result


def save_stats(run_data):
    """Append run data to stats.json."""
    stats = []
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                stats = json.load(f)
            if not isinstance(stats, list):
                stats = []
        except (json.JSONDecodeError, IOError):
            stats = []
    stats.append(run_data)
    try:
        tmp_path = STATS_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(stats, f, indent=2)
        os.replace(tmp_path, STATS_FILE)
    except OSError as e:
        print(f"Warning: could not save stats: {e}")


def save_settings():
    """Save current display settings to settings.json."""
    data = {
        "resolution_index": options_resolution_index,
        "fullscreen": options_fullscreen,
        "resolution": list(SUPPORTED_RESOLUTIONS[options_resolution_index]),
    }
    try:
        tmp_path = SETTINGS_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, SETTINGS_FILE)
    except OSError as e:
        print(f"Warning: could not save settings: {e}")


def load_settings():
    """Load display settings from settings.json.

    Returns True if settings were loaded, False if defaults should be used.
    Falls back to auto-detected defaults if file is missing or invalid.
    """
    global options_resolution_index, options_fullscreen
    if not os.path.exists(SETTINGS_FILE):
        return False
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False
        # Determine valid resolution first
        resolved = False
        # Try to match the saved resolution tuple
        if "resolution" in data and isinstance(data["resolution"], list) and len(data["resolution"]) == 2:
            saved_res = tuple(data["resolution"])
            if saved_res in SUPPORTED_RESOLUTIONS:
                options_resolution_index = SUPPORTED_RESOLUTIONS.index(saved_res)
                resolved = True
        # Fall back to resolution_index if resolution tuple doesn't match
        if not resolved and "resolution_index" in data and isinstance(data["resolution_index"], int):
            idx = data["resolution_index"]
            if 0 <= idx < len(SUPPORTED_RESOLUTIONS):
                options_resolution_index = idx
                resolved = True
        if not resolved:
            return False
        # Apply fullscreen only when resolution was also validated
        if "fullscreen" in data and isinstance(data["fullscreen"], bool):
            options_fullscreen = data["fullscreen"]
        return True
    except (json.JSONDecodeError, IOError, KeyError):
        return False


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
        """Fire at target. weapon_stats is a list of weapon dicts (inventory), or None for allies."""
        if weapon_stats is not None:
            # Multi-weapon inventory: fire each weapon on its own cooldown
            dx, dy = target.x - self.x, target.y - self.y
            for ws in weapon_stats:
                if ws.get("cooldown", 0) > 0:
                    ws["cooldown"] -= 1
                    continue
                self._fire_weapon(ws, dx, dy, bullets)
            return
        # Ally path (no weapon_stats)
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        dx, dy = target.x - self.x, target.y - self.y
        shoot_dist = Bullet.LIFETIME * Bullet.SPEED
        if math.hypot(dx, dy) < shoot_dist:
            self._fire_single("normal", 1, Bullet.SPEED, Bullet.LIFETIME, dx, dy, bullets)
            self.cooldown = self.SHOOT_COOLDOWN

    def _fire_weapon(self, ws, dx, dy, bullets):
        """Fire a single weapon from the inventory."""
        fire_rate = ws["fire_rate"]
        bullet_speed = ws["bullet_speed"]
        bullet_range = ws["range"]
        damage = ws["damage"]
        weapon_type = ws["weapon_type"]
        shoot_dist = bullet_range * bullet_speed
        if math.hypot(dx, dy) < shoot_dist:
            self._fire_single(weapon_type, damage, bullet_speed, bullet_range, dx, dy, bullets)
            ws["cooldown"] = fire_rate

    def _fire_single(self, weapon_type, damage, bullet_speed, bullet_range, dx, dy, bullets):
        """Create bullet(s) for one weapon firing."""
        if weapon_type == "shotgun":
            base_angle = math.atan2(dy, dx)
            spread_angle = math.radians(30)
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
    "basic": {"hp": 3, "speed": 1.4, "radius": 12, "color": (255, 30, 60), "xp_value": 2},
    "runner": {"hp": 2, "speed": 2.2, "radius": 8, "color": (230, 255, 0), "xp_value": 2},
    "brute": {"hp": 9, "speed": 0.9, "radius": 18, "color": (255, 140, 0), "xp_value": 5},
    "shielded": {"hp": 6, "speed": 1.0, "radius": 14, "color": (0, 255, 255), "xp_value": 6, "shield": True},
    "splitter": {"hp": 4, "speed": 1.0, "radius": 14, "color": (0, 255, 100), "xp_value": 3},
    "mini": {"hp": 2, "speed": 1.8, "radius": 7, "color": (0, 255, 100), "xp_value": 1},
    "elite": {"hp": 15, "speed": 1.8, "radius": 16, "color": (255, 0, 255), "xp_value": 12},
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

    def __init__(self, camera, enemy_type="basic", wave=1):
        Enemy._next_id += 1
        self.uid = Enemy._next_id
        self.enemy_type = enemy_type
        type_cfg = ENEMY_TYPES[enemy_type]
        base_hp = type_cfg["hp"]
        linear = 1 + 0.12 * (wave - 1)
        compound = 1.06 ** max(0, wave - 20)
        self.hp = max(base_hp, int(base_hp * linear * compound))
        base_speed = type_cfg["speed"]
        self.speed = base_speed * min(2.0, 1 + 0.02 * (wave - 1))
        self.radius = type_cfg["radius"]
        self.color = type_cfg["color"]
        base_xp = type_cfg["xp_value"]
        self.xp_value = base_xp + wave // 5
        self.shield = type_cfg.get("shield", False)
        self.contact_damage = 1 + (wave - 1) // 5
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
        self.lifetime = self.LIFETIME
        self.collected = False

    def update(self, player):
        self.lifetime -= 1
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.COLLECT_RANGE:
            self.collected = True
            return
        if self.lifetime <= 0:
            return
        if dist < self.ATTRACT_RANGE and dist > 0:
            self.x += dx / dist * self.ATTRACT_SPEED
            self.y += dy / dist * self.ATTRACT_SPEED

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        fade = max(0.3, self.lifetime / self.LIFETIME)
        color = tuple(int(c * fade) for c in HEALTH_PICKUP_COLOR)
        draw_glow(screen, color, (sx, sy), self.RADIUS, intensity=100, layers=5)
        pygame.draw.circle(screen, color, (sx, sy), self.RADIUS)
        # Cross symbol
        cx_half = self.RADIUS // 2
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
    {"name": "+Max HP", "stat": "max_hp", "amount": 1},
]

WEAPON_TYPES = ["shotgun", "piercing", "explosive"]


def get_scaled_amount(stat, base_amount, level):
    """Scale upgrade amounts based on player level."""
    if stat == "damage":
        if level >= 20:
            return base_amount + 1  # +2 total (reduced from +3)
        elif level >= 10:
            return base_amount  # +1 total (reduced from +2)
    elif stat == "fire_rate":
        if level >= 15:
            return base_amount - 2  # -5 total
    return base_amount


def generate_upgrade_options(level, weapon_stats):
    """Generate 3 upgrade options. At milestone levels, one is a weapon type.

    weapon_stats is a list of weapon dicts (inventory).
    """
    options = random.sample(STAT_UPGRADES, min(3, len(STAT_UPGRADES)))
    options = [dict(o) for o in options]  # copy
    # Scale amounts based on level
    for opt in options:
        if "stat" in opt:
            opt["amount"] = get_scaled_amount(opt["stat"], opt["amount"], level)
    milestone_interval = 4 if level > 15 else 5
    is_milestone = level % milestone_interval == 0
    if is_milestone:
        owned_types = {w["weapon_type"] for w in weapon_stats}
        available_weapons = [w for w in WEAPON_TYPES if w not in owned_types]
        if available_weapons:
            weapon = random.choice(available_weapons)
            options[random.randint(0, len(options) - 1)] = {
                "name": f"Weapon: {weapon.title()}",
                "weapon_type": weapon,
            }
    return options


def apply_upgrade(weapon_stats, option, player=None):
    """Apply an upgrade option to weapon stats. Returns updated stats.

    weapon_stats is a list of weapon dicts (inventory).
    Stat upgrades apply to ALL weapons, weapon_type adds a new weapon entry.
    """
    if "weapon_type" in option:
        # Add new weapon with default stats plus accumulated global bonuses
        defaults = default_weapon_stats()
        new_weapon = dict(defaults)
        new_weapon["weapon_type"] = option["weapon_type"]
        new_weapon["cooldown"] = 0
        # Copy stat bonuses from first weapon (reference weapon)
        ref = weapon_stats[0]
        for stat_key in ("damage", "fire_rate", "bullet_speed", "range"):
            bonus = ref[stat_key] - defaults[stat_key]
            new_weapon[stat_key] += bonus
        new_weapon["fire_rate"] = max(5, new_weapon["fire_rate"])
        weapon_stats.append(new_weapon)
    elif option.get("stat") == "max_hp":
        if player is None:
            raise ValueError("apply_upgrade: 'max_hp' upgrade requires a player argument")
        player.max_hp += option["amount"]
        player.hp = min(player.hp + option["amount"], player.max_hp)
    else:
        for ws in weapon_stats:
            ws[option["stat"]] += option["amount"]
            if option["stat"] == "fire_rate":
                ws["fire_rate"] = max(5, ws["fire_rate"])
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


HUD_MARGIN = 10  # Spacing from screen edges for all HUD widgets


def draw_hud_panel(x, y, w, h, border_color=BORDER_COLOR):
    """Draw a semi-transparent rounded-rect panel with neon border and subtle glow."""
    # Subtle glow behind the border
    glow_layers = 3
    for i in range(glow_layers, 0, -1):
        expand = i * 2
        alpha = max(8, 40 // i)
        glow_color = (border_color[0], border_color[1], border_color[2], alpha)
        glow_surf = _get_glow_surface((w + expand * 2, h + expand * 2))
        glow_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(glow_surf, glow_color,
                         (0, 0, w + expand * 2, h + expand * 2),
                         border_radius=6 + expand)
        screen.blit(glow_surf, (x - expand, y - expand))
    # Panel background
    panel = _get_glow_surface((w, h))
    panel.fill((0, 0, 0, 0))
    pygame.draw.rect(panel, PANEL_BG_COLOR, (0, 0, w, h), border_radius=6)
    screen.blit(panel, (x, y))
    pygame.draw.rect(screen, border_color, (x, y, w, h), 2, border_radius=6)


# Small font for HUD labels
_hud_font = None
_hud_font_small = None


def _get_hud_fonts():
    global _hud_font, _hud_font_small
    if _hud_font is None:
        _hud_font = pygame.font.SysFont(None, 28)
        _hud_font_small = pygame.font.SysFont(None, 22)
    return _hud_font, _hud_font_small


def draw_hud_vitals(player, xp, xp_thresholds, level):
    """Draw top-left vitals widget: HP bar with numeric, XP bar with level badge."""
    hud_font, hud_font_small = _get_hud_fonts()

    panel_x, panel_y = HUD_MARGIN, HUD_MARGIN
    panel_w, panel_h = 220, 80
    draw_hud_panel(panel_x, panel_y, panel_w, panel_h)

    pad = 10
    bar_x = panel_x + pad
    bar_w = panel_w - 2 * pad

    # -- HP bar --
    hp_label_y = panel_y + 8
    hp_bar_y = panel_y + 26
    hp_bar_h = 14

    hp_label = hud_font_small.render("HP", True, HEALTH_FG)
    screen.blit(hp_label, (bar_x, hp_label_y))

    hp_num_text = f"{max(0, player.hp)}/{player.max_hp}"
    hp_num = hud_font_small.render(hp_num_text, True, HEALTH_FG)
    screen.blit(hp_num, (bar_x + bar_w - hp_num.get_width(), hp_label_y))

    hp_frac = max(0, player.hp) / max(1, player.max_hp)
    hp_fill = int(bar_w * hp_frac)
    pygame.draw.rect(screen, HEALTH_BG, (bar_x, hp_bar_y, bar_w, hp_bar_h), border_radius=3)
    if hp_fill > 0:
        pygame.draw.rect(screen, HEALTH_FG, (bar_x, hp_bar_y, hp_fill, hp_bar_h), border_radius=3)
    pygame.draw.rect(screen, HEALTH_FG, (bar_x, hp_bar_y, bar_w, hp_bar_h), 1, border_radius=3)

    # -- XP bar --
    xp_label_y = panel_y + 46
    xp_bar_y = panel_y + 60
    xp_bar_h = 10

    lv_label = hud_font_small.render(f"Lv {level}", True, BORDER_COLOR)
    screen.blit(lv_label, (bar_x, xp_label_y))

    if level - 1 >= len(xp_thresholds):
        # Max level reached - show "MAX" instead of XP progress
        max_label = hud_font_small.render("MAX", True, BORDER_COLOR)
        screen.blit(max_label, (bar_x + bar_w - max_label.get_width(), xp_label_y))
        xp_fill = bar_w
    else:
        current_threshold = xp_thresholds[level - 1]
        xp_text = f"{xp}/{current_threshold}"
        xp_num = hud_font_small.render(xp_text, True, BORDER_COLOR)
        screen.blit(xp_num, (bar_x + bar_w - xp_num.get_width(), xp_label_y))
        xp_frac = min(1.0, xp / max(1, current_threshold))
        xp_fill = int(bar_w * xp_frac)
    pygame.draw.rect(screen, HEALTH_BG, (bar_x, xp_bar_y, bar_w, xp_bar_h), border_radius=3)
    if xp_fill > 0:
        pygame.draw.rect(screen, BORDER_COLOR, (bar_x, xp_bar_y, xp_fill, xp_bar_h), border_radius=3)
    pygame.draw.rect(screen, BORDER_COLOR, (bar_x, xp_bar_y, bar_w, xp_bar_h), 1, border_radius=3)


# Weapon type -> display color mapping for HUD
_WEAPON_TYPE_COLORS = {
    "normal": BULLET_COLOR,
    "shotgun": (255, 180, 0),
    "piercing": (0, 255, 255),
    "explosive": (255, 80, 60),
}


def draw_hud_stats(score, wave, allies):
    """Draw top-right stats widget: score, wave counter, squad size."""
    hud_font, hud_font_small = _get_hud_fonts()

    panel_w, panel_h = 180, 80
    panel_x = WIDTH - panel_w - HUD_MARGIN
    panel_y = HUD_MARGIN
    draw_hud_panel(panel_x, panel_y, panel_w, panel_h)

    pad = 10
    tx = panel_x + pad
    right_x = panel_x + panel_w - pad

    # Score
    score_label = hud_font_small.render("Score", True, BORDER_COLOR)
    screen.blit(score_label, (tx, panel_y + 8))
    score_val = hud_font.render(str(score), True, PLAYER_COLOR)
    screen.blit(score_val, (right_x - score_val.get_width(), panel_y + 6))

    # Wave
    wave_label = hud_font_small.render("Wave", True, BORDER_COLOR)
    screen.blit(wave_label, (tx, panel_y + 30))
    wave_val = hud_font.render(str(wave), True, PLAYER_COLOR)
    screen.blit(wave_val, (right_x - wave_val.get_width(), panel_y + 28))

    # Squad size
    squad_label = hud_font_small.render("Squad", True, BORDER_COLOR)
    screen.blit(squad_label, (tx, panel_y + 52))
    squad_count = 1 + len(allies)  # player + allies
    squad_val = hud_font.render(str(squad_count), True, PLAYER_COLOR)
    screen.blit(squad_val, (right_x - squad_val.get_width(), panel_y + 50))


def draw_hud_weapons(weapon_inventory):
    """Draw bottom-left weapon widget: list active weapons with colored type indicators."""
    hud_font, hud_font_small = _get_hud_fonts()

    line_h = 22
    pad = 10
    panel_w = 180
    panel_h = pad * 2 + max(1, len(weapon_inventory)) * line_h
    panel_x = HUD_MARGIN
    panel_y = HEIGHT - panel_h - HUD_MARGIN
    draw_hud_panel(panel_x, panel_y, panel_w, panel_h)

    tx = panel_x + pad
    for i, w in enumerate(weapon_inventory):
        wtype = w.get("weapon_type", "normal")
        color = _WEAPON_TYPE_COLORS.get(wtype, BULLET_COLOR)
        y = panel_y + pad + i * line_h

        # Color indicator dot
        pygame.draw.circle(screen, color, (tx + 5, y + 8), 5)

        # Weapon name
        label = hud_font_small.render(wtype.capitalize(), True, color)
        screen.blit(label, (tx + 16, y))

        # Damage value on the right
        dmg_text = hud_font_small.render(f"dmg {w.get('damage', 1)}", True, (150, 150, 160))
        screen.blit(dmg_text, (panel_x + panel_w - pad - dmg_text.get_width(), y))


def draw_hud_minimap(camera, player, allies, enemies, obstacles, escape_rooms=None):
    """Draw bottom-right minimap widget showing scaled-down world overview."""
    mm_w, mm_h = 150, 112
    pad = 4
    panel_w = mm_w + pad * 2
    panel_h = mm_h + pad * 2
    panel_x = WIDTH - panel_w - HUD_MARGIN
    panel_y = HEIGHT - panel_h - HUD_MARGIN

    draw_hud_panel(panel_x, panel_y, panel_w, panel_h)

    # Create minimap surface (reuse cached surface)
    mm_surf = _get_glow_surface((mm_w, mm_h))
    mm_surf.fill((0, 0, 0, 0))
    mm_surf.fill((5, 5, 15, 160))

    scale_x = mm_w / MAP_WIDTH
    scale_y = mm_h / MAP_HEIGHT

    # Draw obstacles
    for obs in obstacles:
        rx = int(obs.x * scale_x)
        ry = int(obs.y * scale_y)
        rw = max(1, int(obs.w * scale_x))
        rh = max(1, int(obs.h * scale_y))
        pygame.draw.rect(mm_surf, (80, 0, 140, 180), (rx, ry, rw, rh))

    # Draw escape rooms
    if escape_rooms:
        for er in escape_rooms:
            rx = int(er.x * scale_x)
            ry = int(er.y * scale_y)
            rw = max(2, int(er.w * scale_x))
            rh = max(2, int(er.h * scale_y))
            pygame.draw.rect(mm_surf, ESCAPE_ROOM_BORDER, (rx, ry, rw, rh), 1)

    # Draw enemies as red dots
    for e in enemies:
        ex = int(e.x * scale_x)
        ey = int(e.y * scale_y)
        pygame.draw.circle(mm_surf, ENEMY_COLOR, (ex, ey), 1)

    # Draw allies as blue dots
    for a in allies:
        ax = int(a.x * scale_x)
        ay = int(a.y * scale_y)
        pygame.draw.circle(mm_surf, (0, 150, 255), (ax, ay), 2)

    # Draw player as cyan dot (larger)
    px = int(player.x * scale_x)
    py = int(player.y * scale_y)
    pygame.draw.circle(mm_surf, PLAYER_COLOR, (px, py), 3)

    # Draw camera viewport rectangle
    vx = int(camera.x * scale_x)
    vy = int(camera.y * scale_y)
    vw = max(1, int(WIDTH * scale_x))
    vh = max(1, int(HEIGHT * scale_y))
    pygame.draw.rect(mm_surf, (150, 0, 255, 100), (vx, vy, vw, vh), 1)

    screen.blit(mm_surf, (panel_x + pad, panel_y + pad))


def draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                    score, wave, level, weapon_inventory, xp, xp_thresholds,
                    health_pickups=None, heal_effects=None,
                    escape_rooms=None, escape_flash_timer=0):
    """Draw the full game scene (background, entities, HUD)."""
    screen.fill(BG)
    draw_grid(camera)
    for obs in obstacles:
        if _is_rect_visible(camera, obs.x, obs.y, obs.w, obs.h):
            obs.draw(camera)
    if escape_rooms:
        for er in escape_rooms:
            if _is_rect_visible(camera, er.x, er.y, er.w, er.h):
                er.draw(camera)
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

    # Escape room flash effect
    if escape_flash_timer > 0:
        flash_surface = _get_glow_surface((WIDTH, HEIGHT))
        flash_surface.fill((0, 0, 0, 0))
        alpha = int(180 * (escape_flash_timer / 15))
        flash_surface.fill((0, 255, 200, alpha))
        screen.blit(flash_surface, (0, 0))

    # HUD - Top-left vitals widget
    draw_hud_vitals(player, xp, xp_thresholds, level)

    # HUD - Top-right stats widget
    draw_hud_stats(score, wave, allies)

    # HUD - Bottom-left weapon widget
    draw_hud_weapons(weapon_inventory)

    # HUD - Bottom-right minimap widget
    draw_hud_minimap(camera, player, allies, enemies, obstacles, escape_rooms)

    # Escape room off-screen indicator
    if escape_rooms:
        for er in escape_rooms:
            _draw_escape_room_indicator(camera, er, player)


def compute_indicator_position(screen_x, screen_y, screen_w, screen_h,
                               margin=40, pad=30):
    """Compute off-screen indicator position. Returns (ix, iy) or None if on-screen."""
    if margin <= screen_x <= screen_w - margin and margin <= screen_y <= screen_h - margin:
        return None  # On screen

    cx, cy = screen_w / 2, screen_h / 2
    dx = screen_x - cx
    dy = screen_y - cy
    dist = math.sqrt(dx * dx + dy * dy)
    if dist == 0:
        return None
    nx, ny = dx / dist, dy / dist

    t_vals = []
    if nx != 0:
        t_vals.append((pad - cx) / nx if nx < 0 else (screen_w - pad - cx) / nx)
    if ny != 0:
        t_vals.append((pad - cy) / ny if ny < 0 else (screen_h - pad - cy) / ny)
    positive_t = [t for t in t_vals if t > 0]
    t = min(positive_t) if positive_t else 1
    ix = max(pad, min(screen_w - pad, cx + nx * t))
    iy = max(pad, min(screen_h - pad, cy + ny * t))
    return ix, iy


def _draw_escape_room_indicator(camera, er, player):
    """Draw an arrow at screen edge pointing toward escape room when off-screen."""
    er_cx = er.x + er.w / 2
    er_cy = er.y + er.h / 2
    sx, sy = camera.apply(er_cx, er_cy)

    result = compute_indicator_position(sx, sy, WIDTH, HEIGHT)
    if result is None:
        return
    ix, iy = result

    # Direction relative to player's screen position
    px, py = camera.apply(player.x, player.y)
    dx, dy = sx - px, sy - py
    dist = math.sqrt(dx * dx + dy * dy)
    if dist == 0:
        return
    nx, ny = dx / dist, dy / dist

    # Pulsing effect synced with escape room
    pulse = 0.6 + 0.4 * math.sin(er.pulse_timer * 0.05)
    color = tuple(int(c * pulse) for c in ESCAPE_ROOM_BORDER)

    # Draw arrow triangle pointing toward escape room
    angle = math.atan2(ny, nx)
    size = 10
    tip_x = ix + nx * size
    tip_y = iy + ny * size
    left_x = ix + math.cos(angle + 2.5) * size
    left_y = iy + math.sin(angle + 2.5) * size
    right_x = ix + math.cos(angle - 2.5) * size
    right_y = iy + math.sin(angle - 2.5) * size
    pygame.draw.polygon(screen, color, [
        (int(tip_x), int(tip_y)),
        (int(left_x), int(left_y)),
        (int(right_x), int(right_y)),
    ])

    # Draw distance text
    world_dx = er_cx - player.x
    world_dy = er_cy - player.y
    world_dist = int(math.sqrt(world_dx * world_dx + world_dy * world_dy))
    dist_text = font.render(str(world_dist), True, color)
    text_x = int(ix - dist_text.get_width() / 2)
    text_y = int(iy - 20)
    text_y = max(5, min(HEIGHT - 20, text_y))
    screen.blit(dist_text, (text_x, text_y))


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
        elif stat == "max_hp":
            # Heart shape
            color = (255, 50, 100)
            pygame.draw.polygon(surf, color, [
                (cx, 28), (4, 14), (4, 8), (10, 4), (cx, 12),
                (22, 4), (28, 8), (28, 14)
            ])

    return surf


def _panel_origin():
    """Return (x, y) for the centered upgrade panel."""
    return (WIDTH - PANEL_WIDTH) // 2, (HEIGHT - PANEL_HEIGHT) // 2


def draw_upgrade_panel(level, upgrade_options):
    """Draw a centered floating panel with neon border for the upgrade selector."""
    panel_x, panel_y = _panel_origin()
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
        screen.blit(glow_surf, (panel_x - expand, panel_y - expand))

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

    # Upgrade option rows (level_up_selected_index is synced from mouse hover each frame)
    selected_idx = level_up_selected_index
    for i, opt in enumerate(upgrade_options):
        row_y = OPTION_START_Y + i * OPTION_ROW_HEIGHT
        row_rect = pygame.Rect(OPTION_PADDING, row_y,
                               PANEL_WIDTH - OPTION_PADDING * 2, OPTION_ROW_HEIGHT - 5)

        hovered = (i == selected_idx)

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

    screen.blit(panel_surf, (panel_x, panel_y))


def get_hovered_upgrade_index(mouse_x, mouse_y, num_options):
    """Return the index of the upgrade option under the mouse, or -1 if none."""
    panel_x, panel_y = _panel_origin()
    local_mx = mouse_x - panel_x
    local_my = mouse_y - panel_y
    for i in range(num_options):
        row_y = OPTION_START_Y + i * OPTION_ROW_HEIGHT
        row_rect = pygame.Rect(OPTION_PADDING, row_y,
                               PANEL_WIDTH - OPTION_PADDING * 2, OPTION_ROW_HEIGHT - 5)
        if row_rect.collidepoint(local_mx, local_my):
            return i
    return -1


def apply_resolution():
    """Apply the current resolution and fullscreen settings."""
    global screen, WIDTH, HEIGHT, options_fullscreen, _menu_background, _fade_overlay, _dim_overlay
    res = SUPPORTED_RESOLUTIONS[options_resolution_index]
    WIDTH, HEIGHT = res
    flags = pygame.FULLSCREEN if options_fullscreen else 0
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except pygame.error:
        # Fallback to windowed mode if fullscreen fails
        options_fullscreen = False
        screen = pygame.display.set_mode((WIDTH, HEIGHT), 0)
    _menu_background = None  # Reset so it regenerates at new size
    _fade_overlay = None
    _dim_overlay = None
    save_settings()


def draw_options_menu():
    """Draw the options menu matching main menu visual style."""
    global _menu_background

    # Draw animated fractal city background
    if _menu_background is None:
        _menu_background = FractalBackground(WIDTH, HEIGHT)
    _menu_background.draw(screen)

    # Title in upper-left area matching main menu style
    options_start_y = MENU_START_Y
    title = title_font.render("Options", True, PLAYER_COLOR)
    title_glow = title_font.render("Options", True, (0, 100, 140))
    tx = MENU_X
    ty = options_start_y - 120
    screen.blit(title_glow, (tx - 2, ty - 2))
    screen.blit(title_glow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))

    items = [
        ("Resolution",
         f"{SUPPORTED_RESOLUTIONS[options_resolution_index][0]}x"
         f"{SUPPORTED_RESOLUTIONS[options_resolution_index][1]}"),
        ("Fullscreen", "On" if options_fullscreen else "Off"),
        ("Back", ""),
    ]

    ticks = pygame.time.get_ticks()

    for i, (label, value) in enumerate(items):
        y = options_start_y + i * MENU_ITEM_HEIGHT
        is_selected = (i == options_selected_index)
        x = MENU_X + (MENU_HOVER_INDENT if is_selected else 0)

        if is_selected:
            glow_color = (255, 140, 0)
            text_color = (255, 255, 255)
            glow_surf = menu_font.render(label, True, glow_color)
            screen.blit(glow_surf, (x - 1, y - 1))
            screen.blit(glow_surf, (x + 1, y + 1))
        else:
            text_color = (180, 180, 180)

        text_surf = menu_font.render(label, True, text_color)
        screen.blit(text_surf, (x, y))

        if value:
            val_color = PLAYER_COLOR if is_selected else (180, 180, 180)
            val_surf = menu_font.render(f"  {value}", True, val_color)
            screen.blit(val_surf, (x + text_surf.get_width(), y))

        # Draw separator line after each item except the last
        if i < len(items) - 1:
            sep_y = y + MENU_ITEM_HEIGHT - 10
            draw_menu_separator(screen, MENU_X, sep_y, 200, ticks)

    pygame.display.flip()


def get_menu_item_rect(index):
    """Return the clickable pygame.Rect for a menu item by index."""
    y = MENU_START_Y + index * MENU_ITEM_HEIGHT
    return pygame.Rect(MENU_X, y, 300, MENU_ITEM_HEIGHT - 5)


def get_hovered_menu_index(mx, my):
    """Return menu item index under mouse position, or -1 if none."""
    for i in range(len(MENU_ITEMS)):
        if get_menu_item_rect(i).collidepoint(mx, my):
            return i
    return -1


def get_hovered_options_index(mx, my):
    """Return options menu item index under mouse position, or -1 if none."""
    for i in range(3):  # Resolution, Fullscreen, Back
        if get_menu_item_rect(i).collidepoint(mx, my):
            return i
    return -1


def draw_menu_separator(surface, x, y, width, ticks):
    """Draw an animated orange line separator between menu items."""
    # Pulsing alpha based on time
    pulse = int(80 + 40 * math.sin(ticks * 0.003))
    color = (255, 140, 0)
    # Draw the line
    pygame.draw.line(surface, color, (x, y), (x + width, y), 1)
    # Animated glow sweep - a brighter spot that moves along the line
    sweep_pos = int((ticks * 0.1) % (width + 40)) - 20
    glow_width = 40
    for i in range(glow_width):
        gx = sweep_pos - glow_width // 2 + i
        if x <= gx <= x + width:
            intensity = max(0, pulse - abs(i - glow_width // 2) * 4)
            glow_color = (255, min(255, intensity + 60), 0)
            pygame.draw.line(surface, glow_color, (gx, y - 1), (gx, y + 1), 1)


def draw_menu():
    global _menu_background, menu_fade_alpha, menu_fade_active

    # Draw animated fractal city background
    if _menu_background is None:
        _menu_background = FractalBackground(WIDTH, HEIGHT)
    _menu_background.draw(screen)

    # Title in upper-left area
    title = title_font.render("Squad Survivors", True, PLAYER_COLOR)
    title_glow = title_font.render("Squad Survivors", True, (0, 100, 140))
    tx = MENU_X
    ty = MENU_START_Y - 120
    screen.blit(title_glow, (tx - 2, ty - 2))
    screen.blit(title_glow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))

    ticks = pygame.time.get_ticks()

    # Draw menu items - Half-Life style
    for i, item_text in enumerate(MENU_ITEMS):
        y = MENU_START_Y + i * MENU_ITEM_HEIGHT
        is_selected = (i == menu_selected_index)
        x = MENU_X + (MENU_HOVER_INDENT if is_selected else 0)

        if is_selected:
            # Orange/white highlight with neon glow
            glow_color = (255, 140, 0)
            text_color = (255, 255, 255)
            glow_surf = menu_font.render(item_text, True, glow_color)
            screen.blit(glow_surf, (x - 1, y - 1))
            screen.blit(glow_surf, (x + 1, y + 1))
        else:
            text_color = (180, 180, 180)

        text_surf = menu_font.render(item_text, True, text_color)
        screen.blit(text_surf, (x, y))

        # Draw separator line after each item except the last
        if i < len(MENU_ITEMS) - 1:
            sep_y = y + MENU_ITEM_HEIGHT - 10
            draw_menu_separator(screen, MENU_X, sep_y, 200, ticks)

    # Fade-in overlay
    if menu_fade_active:
        global _fade_overlay
        menu_fade_alpha = min(menu_fade_alpha + 8, 255)
        if menu_fade_alpha < 255:
            if _fade_overlay is None or _fade_overlay.get_size() != (WIDTH, HEIGHT):
                _fade_overlay = pygame.Surface((WIDTH, HEIGHT))
            _fade_overlay.fill(BG)
            _fade_overlay.set_alpha(255 - menu_fade_alpha)
            screen.blit(_fade_overlay, (0, 0))
        else:
            menu_fade_active = False

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
    global options_selected_index, options_resolution_index, options_fullscreen
    global menu_selected_index, active_joystick
    global level_up_selected_index, _gamepad_nav_last_time, _last_levelup_mouse_pos
    init_pygame()
    state = STATE_MENU
    camera = Camera()
    player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
    obstacles = []
    escape_rooms = []
    allies = []
    enemies = []
    bullets = []
    health_pickups = []
    heal_effects = []
    escape_flash_timer = 0
    score = 0
    spawn_timer = 0
    spawn_interval = 110  # frames between spawns
    wave = 1
    wave_timer = 0
    xp = 0
    level = 1
    xp_thresholds = generate_xp_thresholds()
    weapon_inventory = default_weapon_inventory()
    upgrade_options = []
    run_stats = default_run_stats()
    run_stats["weapons_used"].add("normal")
    run_stats["weapon_picks"]["normal"] = 1
    run_start_time = time.time()
    total_xp_earned = 0

    def reset_game():
        nonlocal camera, player, obstacles, escape_rooms, allies, enemies, bullets, health_pickups, heal_effects, score
        nonlocal spawn_timer, spawn_interval, wave, wave_timer
        nonlocal xp, level, weapon_inventory, upgrade_options, escape_flash_timer
        nonlocal run_stats, run_start_time, total_xp_earned
        camera = Camera()
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        obstacles = generate_obstacles()
        er = EscapeRoom(0, 0)
        er.relocate(obstacles)
        escape_rooms = [er]
        allies = []
        enemies = []
        bullets = []
        health_pickups = []
        heal_effects = []
        escape_flash_timer = 0
        score = 0
        spawn_timer = 0
        spawn_interval = 110
        wave = 1
        wave_timer = 0
        xp = 0
        level = 1
        weapon_inventory = default_weapon_inventory()
        upgrade_options = []
        run_stats = default_run_stats()
        run_stats["weapons_used"].add("normal")
        run_stats["weapon_picks"]["normal"] = 1
        run_start_time = time.time()
        total_xp_earned = 0

    def save_if_playing():
        """Save stats if a game is in progress (playing or level-up)."""
        if state in (STATE_PLAYING, STATE_LEVEL_UP):
            survival_time = time.time() - run_start_time
            run_data = collect_run_stats(
                run_stats, score, level, wave, total_xp_earned,
                survival_time, weapon_inventory)
            run_data["quit"] = True
            save_stats(run_data)

    def apply_chosen_upgrade(opt):
        """Apply the chosen upgrade and log it."""
        nonlocal upgrade_options, state
        weapon_snapshot = snapshot_weapon_power(weapon_inventory)
        apply_upgrade(weapon_inventory, opt, player)
        if "weapon_type" in opt:
            wt = opt["weapon_type"]
            run_stats["weapons_used"].add(wt)
            run_stats["weapon_picks"][wt] = run_stats["weapon_picks"].get(wt, 0) + 1
        run_stats["level_logs"].append({
            "level": level,
            "wave": wave,
            "time": round(time.time() - run_start_time, 1),
            "chosen": opt.get("name", opt.get("weapon_type", "?")),
            "options": [o.get("name", o.get("weapon_type", "?")) for o in upgrade_options],
            "weapons": weapon_snapshot,
            "player_hp": player.hp,
            "player_max_hp": player.max_hp,
            "total_damage_taken": run_stats["damage_taken"],
        })
        upgrade_options = []
        state = STATE_PLAYING

    running = True

    while running:
        # Sync level_up_selected_index with mouse hover only when the mouse
        # has actually moved, so a stationary cursor doesn't override gamepad.
        if state == STATE_LEVEL_UP and upgrade_options:
            _mx, _my = pygame.mouse.get_pos()
            if (_mx, _my) != _last_levelup_mouse_pos:
                _last_levelup_mouse_pos = (_mx, _my)
                _hover = get_hovered_upgrade_index(_mx, _my, len(upgrade_options))
                if _hover >= 0:
                    level_up_selected_index = _hover

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_if_playing()
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == STATE_OPTIONS:
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_PLAYING:
                        save_if_playing()
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_GAME_OVER:
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_LEVEL_UP:
                        save_if_playing()
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_MENU:
                        running = False
                elif state == STATE_OPTIONS:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        options_selected_index = (options_selected_index - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        options_selected_index = (options_selected_index + 1) % 3
                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                        if options_selected_index == 0:
                            options_resolution_index = (
                                options_resolution_index + direction
                            ) % len(SUPPORTED_RESOLUTIONS)
                            apply_resolution()
                        elif options_selected_index == 1:
                            options_fullscreen = not options_fullscreen
                            apply_resolution()
                    elif event.key == pygame.K_RETURN:
                        if options_selected_index == 2:
                            state = STATE_MENU
                            _reset_menu_state()
                elif state == STATE_LEVEL_UP and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(upgrade_options):
                        apply_chosen_upgrade(upgrade_options[idx])
                elif state == STATE_MENU:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        menu_selected_index = (menu_selected_index - 1) % len(MENU_ITEMS)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_selected_index = (menu_selected_index + 1) % len(MENU_ITEMS)
                    elif event.key == pygame.K_RETURN:
                        if menu_selected_index == 0:  # NEW GAME
                            reset_game()
                            state = STATE_PLAYING
                        elif menu_selected_index == 1:  # OPTIONS
                            options_selected_index = 0
                            state = STATE_OPTIONS
                        elif menu_selected_index == 2:  # QUIT
                            running = False
                elif event.key == pygame.K_RETURN:
                    if state == STATE_GAME_OVER:
                        reset_game()
                        state = STATE_PLAYING
            if event.type == pygame.MOUSEMOTION and state == STATE_OPTIONS:
                idx = get_hovered_options_index(event.pos[0], event.pos[1])
                if idx >= 0:
                    options_selected_index = idx
            if event.type == pygame.MOUSEMOTION and state == STATE_MENU:
                idx = get_hovered_menu_index(event.pos[0], event.pos[1])
                if idx >= 0:
                    menu_selected_index = idx
            if event.type == pygame.MOUSEMOTION and state == STATE_LEVEL_UP and upgrade_options:
                idx = get_hovered_upgrade_index(event.pos[0], event.pos[1], len(upgrade_options))
                if idx >= 0:
                    level_up_selected_index = idx
            if event.type == pygame.JOYDEVICEADDED:
                active_joystick = handle_joy_device_added(active_joystick, event.device_index)
            if event.type == pygame.JOYDEVICEREMOVED:
                active_joystick = handle_joy_device_removed(active_joystick, event.instance_id)
            _joy_btn_match = False
            if event.type == pygame.JOYBUTTONDOWN and active_joystick is not None:
                try:
                    _joy_btn_match = event.instance_id == active_joystick.get_instance_id()
                except pygame.error:
                    active_joystick = None
                    try:
                        if pygame.joystick.get_count() > 0:
                            active_joystick = pygame.joystick.Joystick(0)
                            active_joystick.init()
                    except pygame.error:
                        pass
            if event.type == pygame.JOYBUTTONDOWN and _joy_btn_match:
                if event.button == 0:  # A button - confirm/select
                    if state == STATE_MENU:
                        if menu_selected_index == 0:  # NEW GAME
                            reset_game()
                            state = STATE_PLAYING
                        elif menu_selected_index == 1:  # OPTIONS
                            options_selected_index = 0
                            state = STATE_OPTIONS
                        elif menu_selected_index == 2:  # QUIT
                            running = False
                    elif state == STATE_OPTIONS:
                        if options_selected_index == 0:  # Resolution - cycle
                            options_resolution_index = (
                                options_resolution_index + 1
                            ) % len(SUPPORTED_RESOLUTIONS)
                            apply_resolution()
                        elif options_selected_index == 1:  # Fullscreen - toggle
                            options_fullscreen = not options_fullscreen
                            apply_resolution()
                        elif options_selected_index == 2:  # Back
                            state = STATE_MENU
                            _reset_menu_state()
                    elif state == STATE_LEVEL_UP and upgrade_options:
                        if 0 <= level_up_selected_index < len(upgrade_options):
                            apply_chosen_upgrade(upgrade_options[level_up_selected_index])
                    elif state == STATE_GAME_OVER:
                        reset_game()
                        state = STATE_PLAYING
                elif event.button == 1:  # B button - back/escape
                    if state == STATE_OPTIONS:
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_LEVEL_UP:
                        save_if_playing()
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_PLAYING:
                        save_if_playing()
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_GAME_OVER:
                        state = STATE_MENU
                        _reset_menu_state()
                    elif state == STATE_MENU:
                        running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == STATE_OPTIONS:
                    idx = get_hovered_options_index(event.pos[0], event.pos[1])
                    if idx == 0:  # Resolution - cycle forward
                        options_resolution_index = (
                            options_resolution_index + 1
                        ) % len(SUPPORTED_RESOLUTIONS)
                        apply_resolution()
                    elif idx == 1:  # Fullscreen - toggle
                        options_fullscreen = not options_fullscreen
                        apply_resolution()
                    elif idx == 2:  # Back
                        state = STATE_MENU
                        _reset_menu_state()
                elif state == STATE_MENU:
                    idx = get_hovered_menu_index(event.pos[0], event.pos[1])
                    if idx == 0:  # NEW GAME
                        reset_game()
                        state = STATE_PLAYING
                    elif idx == 1:  # OPTIONS
                        options_selected_index = 0
                        state = STATE_OPTIONS
                    elif idx == 2:  # QUIT
                        running = False
                elif state == STATE_LEVEL_UP and upgrade_options:
                    idx = get_hovered_upgrade_index(event.pos[0], event.pos[1], len(upgrade_options))
                    if 0 <= idx < len(upgrade_options):
                        apply_chosen_upgrade(upgrade_options[idx])

        # Gamepad D-pad/stick navigation for menu states (with repeat delay)
        if active_joystick is not None and state != STATE_PLAYING:
            now = time.monotonic()
            nav_x, nav_y = 0, 0
            try:
                # Analog stick
                if active_joystick.get_numaxes() >= 2:
                    axis_x = active_joystick.get_axis(0)
                    axis_y = active_joystick.get_axis(1)
                    if abs(axis_x) > JOYSTICK_DEADZONE:
                        nav_x = 1 if axis_x > 0 else -1
                    if abs(axis_y) > JOYSTICK_DEADZONE:
                        nav_y = 1 if axis_y > 0 else -1
                # D-pad
                if active_joystick.get_numhats() > 0:
                    hat_x, hat_y = active_joystick.get_hat(0)
                    if hat_x:
                        nav_x = hat_x
                    if hat_y:
                        nav_y = -hat_y  # SDL hat y is inverted
            except pygame.error:
                active_joystick = None
                nav_x, nav_y = 0, 0
                try:
                    if pygame.joystick.get_count() > 0:
                        active_joystick = pygame.joystick.Joystick(0)
                        active_joystick.init()
                except pygame.error:
                    pass
            if (nav_x or nav_y) and (now - _gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY):
                _gamepad_nav_last_time = now
                if state == STATE_MENU:
                    if nav_y:
                        menu_selected_index = (menu_selected_index + (1 if nav_y > 0 else -1)) % len(MENU_ITEMS)
                elif state == STATE_OPTIONS:
                    current_options_idx = options_selected_index
                    if nav_y:
                        options_selected_index = (options_selected_index + (1 if nav_y > 0 else -1)) % 3
                    elif nav_x:
                        direction = 1 if nav_x > 0 else -1
                        if current_options_idx == 0:
                            options_resolution_index = (
                                (options_resolution_index + direction)
                                % len(SUPPORTED_RESOLUTIONS))
                            apply_resolution()
                        elif current_options_idx == 1:
                            options_fullscreen = not options_fullscreen
                            apply_resolution()
                elif state == STATE_LEVEL_UP and upgrade_options:
                    if nav_y:
                        delta = 1 if nav_y > 0 else -1
                        level_up_selected_index = (
                            (level_up_selected_index + delta)
                            % len(upgrade_options))

        if state == STATE_MENU:
            draw_menu()
            clock.tick(FPS)
            continue

        if state == STATE_OPTIONS:
            draw_options_menu()
            clock.tick(FPS)
            continue

        if state == STATE_GAME_OVER:
            draw_game_over(score, level)
            clock.tick(FPS)
            continue

        if state == STATE_LEVEL_UP:
            draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                            score, wave, level, weapon_inventory, xp, xp_thresholds,
                            health_pickups, heal_effects, escape_rooms)
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

        # Gamepad input
        if active_joystick is not None:
            try:
                # Left analog stick
                if active_joystick.get_numaxes() >= 2:
                    axis_x = active_joystick.get_axis(0)
                    axis_y = active_joystick.get_axis(1)
                    if abs(axis_x) > JOYSTICK_DEADZONE:
                        mx += axis_x
                    if abs(axis_y) > JOYSTICK_DEADZONE:
                        my += axis_y
                # D-pad (hat 0)
                if active_joystick.get_numhats() > 0:
                    hat_x, hat_y = active_joystick.get_hat(0)
                    mx += hat_x
                    my -= hat_y  # SDL hat y is inverted (up=1, down=-1)
            except pygame.error:
                active_joystick = None
                try:
                    if pygame.joystick.get_count() > 0:
                        active_joystick = pygame.joystick.Joystick(0)
                        active_joystick.init()
                except pygame.error:
                    pass
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

        # Check escape room entry
        for er in escape_rooms:
            if er.collides_circle(player.x, player.y, player.RADIUS):
                # Eliminate all on-screen enemies
                er_killed = 0
                er_xp = 0
                er_dead = []
                surviving_enemies = []
                for e in enemies:
                    if _is_visible(camera, e.x, e.y):
                        er_killed += 1
                        er_xp += e.xp_value
                        er_dead.append((e.x, e.y, e.enemy_type))
                    else:
                        surviving_enemies.append(e)
                enemies = surviving_enemies
                score += er_killed
                total_xp_earned += er_xp
                xp += er_xp
                run_stats["wave_kills"] += er_killed
                run_stats["wave_xp_earned"] += er_xp
                xp, level, leveled_up = check_level_up(xp, level, xp_thresholds)
                if leveled_up:
                    upgrade_options = generate_upgrade_options(level, weapon_inventory)
                    for opt in upgrade_options:
                        opt['_icon'] = create_upgrade_icon(opt)
                    level_up_selected_index = 0
                    _last_levelup_mouse_pos = pygame.mouse.get_pos()
                    state = STATE_LEVEL_UP
                # Health pickup drops
                for dx, dy, etype in er_dead:
                    if random.random() < get_health_drop_chance(etype):
                        health_pickups.append(HealthPickup(dx, dy))
                # Ally spawns
                for _ in range(er_killed):
                    if random.random() < 0.1:
                        color = random.choice(ALLY_COLORS)
                        a = Unit(player.x + random.uniform(-30, 30),
                                 player.y + random.uniform(-30, 30), color)
                        allies.append(a)
                er.relocate(obstacles, escape_rooms)
                escape_flash_timer = 15
                break

        # If escape room triggered a level-up, skip rest of frame
        if state == STATE_LEVEL_UP:
            draw_game_scene(
                camera, obstacles, bullets, enemies, allies,
                player, score, wave, level, weapon_inventory,
                xp, xp_thresholds, health_pickups,
                heal_effects, escape_rooms)
            draw_dim_overlay()
            draw_upgrade_panel(level, upgrade_options)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # Spawn enemies
        spawn_timer += 1
        wave_timer += 1
        if wave_timer > 480:
            # Log completed wave stats before advancing
            run_stats["wave_logs"].append({
                "wave": wave,
                "kills": run_stats["wave_kills"],
                "damage_dealt": run_stats["wave_damage_dealt"],
                "damage_taken": run_stats["wave_damage_taken"],
                "xp_earned": run_stats["wave_xp_earned"],
                "player_hp": player.hp,
                "player_max_hp": player.max_hp,
                "enemy_count": len(enemies),
                "level": level,
                "time": round(time.time() - run_start_time, 1),
            })
            run_stats["wave_damage_dealt"] = 0
            run_stats["wave_damage_taken"] = 0
            run_stats["wave_kills"] = 0
            run_stats["wave_xp_earned"] = 0
            wave += 1
            wave_timer = 0
            spawn_interval = max(10, spawn_interval - 14)
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            for _ in range(get_spawn_count(wave)):
                if len(enemies) >= get_max_enemies(wave):
                    break
                etype = get_enemy_type_for_wave(wave)
                enemies.append(Enemy(camera, enemy_type=etype, wave=wave))

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
                ws = weapon_inventory if u.is_player else None
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
                    actual_dmg = min(b.damage, max(e.hp, 0))
                    e.hp -= b.damage
                    run_stats["damage_dealt"] += actual_dmg
                    run_stats["wave_damage_dealt"] += actual_dmg
                    wt = b.weapon_type or "normal"
                    run_stats["weapon_damage"][wt] = run_stats["weapon_damage"].get(wt, 0) + actual_dmg
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
                        run_stats["weapon_kills"][wt] = run_stats["weapon_kills"].get(wt, 0) + 1
                        run_stats["wave_kills"] += 1
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
                        actual_edmg = min(edmg, max(e.hp, 0))
                        e.hp -= edmg
                        run_stats["damage_dealt"] += actual_edmg
                        run_stats["wave_damage_dealt"] += actual_edmg
                        run_stats["weapon_damage"]["explosive"] = (
                            run_stats["weapon_damage"].get("explosive", 0)
                            + actual_edmg)
                        if e.hp <= 0:
                            killed += 1
                            xp_earned += e.xp_value
                            dead_enemies.append((e.x, e.y, e.enemy_type))
                            run_stats["weapon_kills"]["explosive"] = run_stats["weapon_kills"].get("explosive", 0) + 1
                            run_stats["wave_kills"] += 1
                            if e.enemy_type == "splitter":
                                split_spawns.append((e.x, e.y))
                            continue
                surviving_after_explosion.append(e)
            enemies = surviving_after_explosion
        # Spawn mini enemies from dead splitters
        for sx, sy in split_spawns:
            for offset in (-12, 12):
                if len(enemies) >= get_max_enemies(wave):
                    break
                mini = Enemy(camera, enemy_type="mini", wave=wave)
                mini.x = sx + offset
                mini.y = sy
                enemies.append(mini)

        score += killed

        # Spawn health pickups from dead enemies
        for dx, dy, etype in dead_enemies:
            if random.random() < get_health_drop_chance(etype):
                health_pickups.append(HealthPickup(dx, dy))

        # Award XP and check level-up
        total_xp_earned += xp_earned
        run_stats["wave_xp_earned"] += xp_earned
        xp += xp_earned
        xp, level, leveled_up = check_level_up(xp, level, xp_thresholds)
        if leveled_up:
            upgrade_options = generate_upgrade_options(level, weapon_inventory)
            for opt in upgrade_options:
                opt['_icon'] = create_upgrade_icon(opt)
            level_up_selected_index = 0
            _last_levelup_mouse_pos = pygame.mouse.get_pos()
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
            for er in escape_rooms:
                e.x, e.y = er.push_circle_out(e.x, e.y, e.radius)

        # Enemy-player collision (damage player)
        surviving = []
        for e in enemies:
            if player.hp > 0 and math.hypot(e.x - player.x, e.y - player.y) < e.radius + player.RADIUS:
                player.hp -= e.contact_damage
                run_stats["damage_taken"] += e.contact_damage
                run_stats["wave_damage_taken"] += e.contact_damage
            else:
                surviving.append(e)
        enemies = surviving

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

        if player.hp <= 0:
            survival_time = time.time() - run_start_time
            run_data = collect_run_stats(
                run_stats, score, level, wave, total_xp_earned,
                survival_time, weapon_inventory)
            save_stats(run_data)
            state = STATE_GAME_OVER

        # Tick escape room pulse timers
        for er in escape_rooms:
            er.pulse_timer += 1

        # Tick escape flash
        if escape_flash_timer > 0:
            escape_flash_timer -= 1

        # Draw
        draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                        score, wave, level, weapon_inventory, xp, xp_thresholds,
                        health_pickups, heal_effects,
                        escape_rooms, escape_flash_timer)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
