import pygame
import math
import random
import sys
import json
import os
import time
from assets_manager import AssetManager, TileRenderer, TiledMapRenderer
from progression import (
    load_profile, save_profile, default_profile,
    generate_upgrade_options as gen_upgrade_options,
    apply_upgrade as prog_apply_upgrade,
    apply_profile_to_game, compute_run_earned_upgrades,
    select_saved_upgrade, save_run_upgrade_to_profile,
    UPGRADE_CATEGORIES, compute_weapon_stats,
)

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        raise ImportError(
            "Python <3.11 requires the 'tomli' package. Install it with: pip install tomli"
        )

BALANCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "balance.toml")
BALANCE = {}


def _default_balance_toml():
    """Return the default balance.toml content as a string."""
    return '''\
# SBU: Nuclear Option - Balance Configuration
# Edit values below to tweak game balance. Delete this file to regenerate defaults.

[player]
hp = 5                  # starting and base max HP
speed = 3.5             # movement speed (pixels per frame)
shoot_cooldown = 25     # frames between ally shots
radius = 14             # collision/draw radius
invulnerable_duration = 120  # frames of invulnerability after taking damage (~2s at 60fps)

[player.ally]
hp = 3                  # ally unit HP
speed = 2.5             # ally movement speed (pixels per frame)
lifetime = 600          # ally lifespan in frames (~10 seconds at 60fps)

[weapons.default]
damage = 1              # base bullet damage
fire_rate = 25          # frames between shots (lower = faster)
bullet_speed = 8        # bullet travel speed (pixels per frame)
range = 90              # bullet lifetime in frames (effective range = speed * range)

[weapons.shotgun]
pellet_count = 5        # number of pellets per shot
spread_angle = 30       # half-spread angle in degrees (pellets span ±this from center)

[weapons.explosive]
radius = 60             # explosion area-of-effect radius in pixels

[bullets.enemy]
speed = 4               # enemy bullet travel speed
radius = 5              # enemy bullet collision radius
lifetime = 120          # enemy bullet lifespan in frames

[enemies.basic]
hp = 3
speed = 1.4
radius = 12
color = [255, 30, 60]
xp_value = 2

[enemies.runner]
hp = 2
speed = 2.2
radius = 8
color = [230, 255, 0]
xp_value = 2

[enemies.brute]
hp = 9
speed = 0.9
radius = 18
color = [255, 140, 0]
xp_value = 5

[enemies.shielded]
hp = 6
speed = 1.0
radius = 14
color = [0, 255, 255]
xp_value = 6
shield = true

[enemies.splitter]
hp = 4
speed = 1.0
radius = 14
color = [0, 255, 100]
xp_value = 3

[enemies.mini]
hp = 2
speed = 1.8
radius = 7
color = [0, 255, 100]
xp_value = 1

[enemies.elite]
hp = 15
speed = 1.8
radius = 16
color = [255, 0, 255]
xp_value = 12

[enemies.shooter]
hp = 5
speed = 0.8
radius = 13
color = [255, 100, 50]
xp_value = 5

[enemies.scaling]
# HP scaling: base_hp * (1 + hp_linear * (wave-1)) * (hp_compound ^ max(0, wave - hp_compound_start))
hp_linear = 0.12               # linear HP growth per wave
hp_compound = 1.06              # compound HP growth factor
hp_compound_start = 20          # wave at which compound scaling kicks in
# Speed scaling: base_speed * min(speed_cap, 1 + speed_linear * (wave-1))
speed_linear = 0.02             # linear speed growth per wave
speed_cap = 2.0                 # maximum speed multiplier
# XP scaling: base_xp + wave // xp_wave_divisor
xp_wave_divisor = 5             # waves per bonus XP point
# Contact damage: 1 + (wave-1) // contact_damage_divisor
contact_damage_divisor = 5      # waves per bonus contact damage

[enemies.shooter_behavior]
shoot_cooldown = 90             # frames between shots (~1.5s at 60fps)
shoot_timer_min = 30            # minimum initial shot delay (stagger)
shoot_timer_max = 90            # maximum initial shot delay (stagger)
approach_distance = 250         # move toward player when farther than this
retreat_distance = 150          # retreat from player when closer than this
firing_distance = 300           # maximum range to fire at player

[splitter]
mini_count = 2                  # number of mini enemies spawned on death
spawn_offset = 12               # pixel offset from splitter death position

[waves]
timer = 480                     # frames per wave (~8 seconds at 60fps)
spawn_interval_base = 110       # starting frames between spawn events
spawn_interval_reduction = 14   # frames removed from spawn interval each wave
spawn_interval_min = 10         # minimum spawn interval floor

# Wave composition: enemy type weights per wave threshold
# Checked in descending order; first matching threshold is used
[[waves.composition]]
threshold = 12
weights = { runner = 10, brute = 10, shielded = 20, splitter = 20, elite = 15, shooter = 25 }

[[waves.composition]]
threshold = 10
weights = { runner = 15, brute = 15, shielded = 20, splitter = 20, elite = 10, shooter = 20 }

[[waves.composition]]
threshold = 8
weights = { runner = 20, brute = 20, shielded = 20, splitter = 25, shooter = 15 }

[[waves.composition]]
threshold = 6
weights = { basic = 30, runner = 25, brute = 20, shielded = 15, splitter = 10 }

[[waves.composition]]
threshold = 3
weights = { basic = 60, runner = 25, brute = 15 }

[[waves.composition]]
threshold = 1
weights = { basic = 100 }

[upgrades]
damage_amount = 1               # base damage increase per upgrade
fire_rate_amount = -3            # base fire rate change per upgrade (negative = faster)
bullet_speed_amount = 2          # base bullet speed increase per upgrade
range_amount = 15                # base range increase per upgrade
max_hp_amount = 1                # HP increase per upgrade
min_fire_rate = 5                # absolute minimum fire rate floor

[upgrades.scaling]
# Level thresholds for bonus scaling on damage upgrades
damage_tier2_level = 10          # level at which damage stays at base
damage_tier3_level = 20          # level at which damage gets +1 bonus
damage_tier3_bonus = 1           # extra damage at tier 3
# Level threshold for bonus scaling on fire rate upgrades
fire_rate_tier2_level = 15       # level at which fire rate gets extra -2
fire_rate_tier2_bonus = -2       # extra fire rate reduction at tier 2
# Milestone intervals for weapon type upgrades
milestone_interval_early = 5     # levels between weapon offers (level <= 15)
milestone_interval_late = 4      # levels between weapon offers (level > 15)
milestone_threshold = 15         # level at which interval switches

[xp]
# Formula: base + linear * i + quadratic * i^2 (where i = level - 1)
base = 10                        # XP needed for level 2
linear = 5                       # linear coefficient
quadratic = 2                    # quadratic coefficient
max_level = 50                   # maximum achievable level

[health_pickups]
radius = 8                       # pickup collision/draw radius
lifetime = 600                   # frames before pickup disappears
attract_range = 100              # distance at which pickup moves toward player
attract_speed = 4.0              # speed of attraction movement
collect_range = 20               # distance at which pickup is collected

[health_pickups.drop_chance]
basic = 0.05
runner = 0.05
brute = 0.12
shielded = 0.08
splitter = 0.06
mini = 0.03
elite = 0.15
shooter = 0.08
default = 0.05                   # fallback for unknown enemy types

[difficulty]
max_enemies_base = 140           # starting enemy cap
max_enemies_cap = 200            # absolute maximum enemies
# Spawn count formula: wave + wave // spawn_count_divisor
spawn_count_divisor = 4          # divisor for bonus spawns per wave
# Max enemies formula: min(cap, base + wave * enemies_per_wave)
enemies_per_wave = 2             # extra enemy cap per wave
'''


_balance_initialized = False


def _rebuild_derived_constants():
    """Rebuild all module-level constants derived from BALANCE.

    Must be called after BALANCE is updated to keep derived state in sync.
    Safe to call before classes are defined (will skip class updates).
    """
    global MAX_ENEMIES_BASE, MAX_ENEMIES_CAP, ENEMY_TYPES, WAVE_COMPOSITION
    global HEALTH_DROP_CHANCE, STAT_UPGRADES
    if not _balance_initialized:
        return
    _diff_cfg = BALANCE.get("difficulty", {})
    MAX_ENEMIES_BASE = _diff_cfg.get("max_enemies_base", 140)
    MAX_ENEMIES_CAP = _diff_cfg.get("max_enemies_cap", 200)
    ENEMY_TYPES = _build_enemy_types()
    WAVE_COMPOSITION = _build_wave_composition()
    HEALTH_DROP_CHANCE = _build_health_drop_chance()
    STAT_UPGRADES = _build_stat_upgrades()
    # Update class-level attributes
    _pcfg = BALANCE.get("player", {})
    Unit.RADIUS = _pcfg.get("radius", 14)
    Unit.PLAYER_SPEED = _pcfg.get("speed", 3.5)
    Unit.SHOOT_COOLDOWN = _pcfg.get("shoot_cooldown", 25)
    Unit.INVULNERABLE_DURATION = _pcfg.get("invulnerable_duration", 120)
    _ally_cfg = _pcfg.get("ally", {})
    Unit.SPEED = _ally_cfg.get("speed", 2.5)
    Unit.ALLY_LIFETIME = _ally_cfg.get("lifetime", 600)
    _eb_cfg = BALANCE.get("bullets", {}).get("enemy", {})
    EnemyBullet.SPEED = _eb_cfg.get("speed", 4)
    EnemyBullet.RADIUS = _eb_cfg.get("radius", 5)
    EnemyBullet.LIFETIME = _eb_cfg.get("lifetime", 120)
    _wcfg = BALANCE.get("weapons", {}).get("default", {})
    Bullet.SPEED = _wcfg.get("bullet_speed", 8)
    Bullet.LIFETIME = _wcfg.get("range", 90)
    _hp_cfg = BALANCE.get("health_pickups", {})
    HealthPickup.RADIUS = _hp_cfg.get("radius", 8)
    HealthPickup.LIFETIME = _hp_cfg.get("lifetime", 600)
    HealthPickup.ATTRACT_RANGE = _hp_cfg.get("attract_range", 100)
    HealthPickup.ATTRACT_SPEED = _hp_cfg.get("attract_speed", 4.0)
    HealthPickup.COLLECT_RANGE = _hp_cfg.get("collect_range", 20)


def load_balance_config():
    """Load balance configuration from balance.toml.

    If the file is missing, generate a default one first.
    Returns the parsed config dict and also stores it in the module-level BALANCE.
    Also rebuilds all derived module-level constants.
    """
    global BALANCE
    if not os.path.exists(BALANCE_FILE):
        try:
            with open(BALANCE_FILE, "w") as f:
                f.write(_default_balance_toml())
        except OSError as e:
            print(f"Warning: could not generate balance.toml: {e}")
            BALANCE = tomllib.loads(_default_balance_toml())
            return BALANCE
    try:
        with open(BALANCE_FILE, "rb") as f:
            BALANCE = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as e:
        print(f"Warning: could not read balance.toml, using defaults: {e}")
        BALANCE = tomllib.loads(_default_balance_toml())
    _rebuild_derived_constants()
    return BALANCE


load_balance_config()

WIDTH, HEIGHT = 1024, 768
MAP_WIDTH, MAP_HEIGHT = 4096, 3072
FPS = 60
_diff_cfg = BALANCE.get("difficulty", {})
MAX_ENEMIES_BASE = _diff_cfg.get("max_enemies_base", 140)
MAX_ENEMIES_CAP = _diff_cfg.get("max_enemies_cap", 200)


def get_max_enemies(wave):
    """Return the enemy cap for a given wave."""
    enemies_per_wave = BALANCE.get("difficulty", {}).get("enemies_per_wave", 2)
    return min(MAX_ENEMIES_CAP, MAX_ENEMIES_BASE + wave * enemies_per_wave)


def get_spawn_count(wave):
    """Return the number of enemies to spawn per spawn event."""
    divisor = int(BALANCE.get("difficulty", {}).get("spawn_count_divisor", 4))
    if divisor <= 0:
        divisor = 4
    return int(wave + wave // divisor)


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


_assets = None  # Global AssetManager instance
_tile_renderer = None  # Global TileRenderer instance


def init_pygame():
    global screen, clock, font, title_font, menu_font, active_joystick, WIDTH, HEIGHT
    global options_fullscreen, _assets, _tile_renderer
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
    # Fullscreen always uses native desktop resolution; saved resolution only applies to windowed
    if options_fullscreen and _native_resolution:
        WIDTH, HEIGHT = _native_resolution
    else:
        WIDTH, HEIGHT = SUPPORTED_RESOLUTIONS[options_resolution_index]
    flags = pygame.FULLSCREEN | pygame.SCALED if options_fullscreen else pygame.SCALED
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except pygame.error:
        # Fallback to windowed mode if fullscreen fails
        options_fullscreen = False
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
        save_settings()
    pygame.display.set_caption("SBU: Nuclear Option")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 72)
    menu_font = pygame.font.SysFont(None, 52)
    # Step 5: Load all sprite assets
    _assets = AssetManager()
    _assets.preload_all(screen_size=(WIDTH, HEIGHT))
    # Step 6: Build tile renderer for background
    # Prefer Tiled .tmx map if available, fall back to procedural
    _tmx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps", "level1.tmx")
    if os.path.exists(_tmx_path):
        _tile_renderer = TiledMapRenderer(_tmx_path, target_tile_size=128)
    else:
        _tile_renderer = TileRenderer(MAP_WIDTH, MAP_HEIGHT, tile_size=128)
        _tile_renderer.build(_assets.get_tiles("grass"), _assets.get_tiles("ground"))
    # Step 7: Load upgrade card assets
    _load_card_assets()


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
STATE_DEATH_REVIEW = 5
STATE_INTRO = 6
STATE_VICTORY = 7

BOMB_PARTS_TOTAL = 10

SUPPORTED_RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1920, 1080),
]

options_selected_index = 0  # 0=resolution, 1=fullscreen, 2=back
options_resolution_index = 1  # default 1024x768
options_fullscreen = True


_native_resolution = None  # Cached native desktop resolution


def detect_native_resolution():
    """Detect native display resolution and add it to SUPPORTED_RESOLUTIONS.

    Must be called after pygame.init() but before pygame.display.set_mode().
    Uses get_desktop_sizes() (recommended over display.Info()) for correct
    resolution on macOS Retina/HiDPI displays.
    Returns the (width, height) tuple of the native resolution.
    Updates options_resolution_index to point to the native resolution.
    """
    global options_resolution_index, _native_resolution
    try:
        desktop_sizes = pygame.display.get_desktop_sizes()
    except (pygame.error, AttributeError):
        # Fallback for older pygame without get_desktop_sizes
        try:
            info = pygame.display.Info()
            desktop_sizes = [(info.current_w, info.current_h)]
        except pygame.error:
            return None
    if not desktop_sizes:
        return None
    native_res = desktop_sizes[0]  # primary display
    if native_res[0] <= 0 or native_res[1] <= 0:
        return None
    _native_resolution = native_res
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

# Colors — classic zombie shooter palette
BG = (30, 25, 20)
PLAYER_COLOR = (220, 180, 80)
ALLY_COLORS = [
    (180, 160, 80), (160, 140, 70), (200, 170, 90),
    (170, 150, 75), (190, 165, 85), (175, 155, 78),
]
ENEMY_COLOR = (180, 40, 40)
BULLET_COLOR = (255, 200, 50)
HEALTH_BG = (60, 60, 60)
HEALTH_FG = (180, 30, 30)
GRID_COLOR = (40, 35, 28)
BORDER_COLOR = (100, 70, 40)
OBSTACLE_COLOR = (50, 40, 30)
OBSTACLE_BORDER = (80, 60, 40)
HEALTH_PICKUP_COLOR = (200, 50, 50)
ESCAPE_ROOM_COLOR = (20, 40, 20)
ESCAPE_ROOM_BORDER = (50, 180, 50)


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


_shadow_cache = {}


def draw_shadow(surface, center, width, height):
    """Draw a dark semi-transparent ellipse shadow under an entity."""
    key = (width, height)
    shadow = _shadow_cache.get(key)
    if shadow is None:
        if len(_shadow_cache) > 128:
            _shadow_cache.clear()
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), (0, 0, width, height))
        _shadow_cache[key] = shadow
    surface.blit(shadow, (center[0] - width // 2, center[1] - height // 4))


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
        self._sprite = None
        if _assets is not None:
            seed = int(x * 1000 + y)
            self._sprite = _assets.get_random_obstacle_sprite(w, h, seed=seed)

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        # Shadow offset below and to the right
        cx = sx + self.w // 2
        cy = sy + self.h // 2
        draw_shadow(screen, (cx + 4, cy + 4), self.w, int(self.h * 0.6))
        if self._sprite is not None:
            screen.blit(self._sprite, (sx, sy))
        else:
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
        # Draw safe zone with pulsing green border
        pygame.draw.rect(screen, ESCAPE_ROOM_COLOR, (sx, sy, self.w, self.h))
        border_col = tuple(int(c * pulse) for c in ESCAPE_ROOM_BORDER)
        pygame.draw.rect(screen, border_col, (sx, sy, self.w, self.h), 3)
        # Cross symbol in center
        cx_s = sx + self.w // 2
        cy_s = sy + self.h // 2
        cross_size = min(self.w, self.h) // 4
        pygame.draw.line(screen, border_col, (cx_s - cross_size, cy_s), (cx_s + cross_size, cy_s), 3)
        pygame.draw.line(screen, border_col, (cx_s, cy_s - cross_size), (cx_s, cy_s + cross_size), 3)

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
    wcfg = BALANCE.get("weapons", {}).get("default", {})
    return {
        "damage": wcfg.get("damage", 1),
        "fire_rate": wcfg.get("fire_rate", 25),
        "bullet_speed": wcfg.get("bullet_speed", 8),
        "range": wcfg.get("range", 90),
        "weapon_type": "normal",
        "cooldown": 0,
    }


def default_weapon_inventory():
    """Return a weapon inventory list containing one normal weapon."""
    return [default_weapon_stats()]


STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
MUSIC_DIR = os.path.dirname(os.path.abspath(__file__))
_current_music = None


def _play_music(filename):
    """Load and loop a music file.

    Silently does nothing if file missing or mixer unavailable.
    Skips reload if the same file is already playing.
    """
    global _current_music
    if filename == _current_music:
        return
    _stop_music()
    filepath = os.path.join(MUSIC_DIR, filename)
    if not os.path.exists(filepath):
        return
    try:
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play(-1)
        _current_music = filename
    except (pygame.error, OSError):
        _current_music = None


def _stop_music():
    """Stop current music playback.

    Silently does nothing if mixer unavailable.
    """
    global _current_music
    try:
        pygame.mixer.music.stop()
    except (pygame.error, OSError):
        pass
    _current_music = None


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
    _wcfg = BALANCE.get("weapons", {}).get("default", {})
    SPEED = _wcfg.get("bullet_speed", 8)
    RADIUS = 4
    LIFETIME = _wcfg.get("range", 90)  # frames

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
        color = _WEAPON_TYPE_COLORS.get(self.weapon_type, BULLET_COLOR)
        pygame.draw.circle(screen, color, (sx, sy), self.RADIUS)


class EnemyBullet:
    _eb_cfg = BALANCE.get("bullets", {}).get("enemy", {})
    SPEED = _eb_cfg.get("speed", 4)
    RADIUS = _eb_cfg.get("radius", 5)
    LIFETIME = _eb_cfg.get("lifetime", 120)

    def __init__(self, x, y, dx, dy, damage=1):
        self.x, self.y = x, y
        length = math.hypot(dx, dy) or 1
        self.vx = dx / length * self.SPEED
        self.vy = dy / length * self.SPEED
        self.life = self.LIFETIME
        self.damage = damage

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    COLOR = (120, 200, 50)  # sickly green for zombie bullets

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        pygame.draw.circle(screen, self.COLOR, (sx, sy), self.RADIUS)


class Unit:
    _pcfg = BALANCE.get("player", {})
    RADIUS = _pcfg.get("radius", 14)
    PLAYER_SPEED = _pcfg.get("speed", 3.5)
    SHOOT_COOLDOWN = _pcfg.get("shoot_cooldown", 25)

    INVULNERABLE_DURATION = _pcfg.get("invulnerable_duration", 120)

    _ally_cfg = BALANCE.get("player", {}).get("ally", {})
    SPEED = _ally_cfg.get("speed", 2.5)
    ALLY_LIFETIME = _ally_cfg.get("lifetime", 600)

    def __init__(self, x, y, color, is_player=False):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.is_player = is_player
        self.cooldown = 0
        pcfg = BALANCE.get("player", {})
        ally_cfg = pcfg.get("ally", {})
        self.max_hp = pcfg.get("hp", 5) if is_player else ally_cfg.get("hp", 3)
        self.hp = self.max_hp
        self.lifetime = -1 if is_player else self.ALLY_LIFETIME
        self.invulnerable_timer = 0
        self.player_speed = self.PLAYER_SPEED  # instance attr, overridable by profile
        self.shoot_target = None  # current enemy being shot at (for facing)
        self.facing_angle = 0.0  # degrees, 0 = up
        self.anim_state = "idle"
        self._prev_x = float(x)
        self._prev_y = float(y)
        # Load sprites
        if _assets is not None:
            prefix = "player" if is_player else "ally"
            self.sprite_idle = _assets.get_animation(f"{prefix}_idle")
            self.sprite_walk = _assets.get_animation(f"{prefix}_walk")
            self.sprite_shoot = _assets.get_animation(f"{prefix}_shoot") if is_player else None
        else:
            self.sprite_idle = None
            self.sprite_walk = None
            self.sprite_shoot = None

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
            shotgun_cfg = BALANCE.get("weapons", {}).get("shotgun", {})
            spread_angle = math.radians(shotgun_cfg.get("spread_angle", 30))
            pellet_count = max(1, int(shotgun_cfg.get("pellet_count", 5)))
            shotgun_damage = max(1, damage // 2)
            for i in range(pellet_count):
                angle = base_angle + spread_angle * (i - (pellet_count - 1) / 2) / max(1, (pellet_count - 1) / 2)
                sdx = math.cos(angle)
                sdy = math.sin(angle)
                bullets.append(Bullet(self.x, self.y, sdx, sdy,
                                      damage=shotgun_damage, speed=bullet_speed,
                                      lifetime=bullet_range, weapon_type="shotgun"))
        else:
            bullets.append(Bullet(self.x, self.y, dx, dy,
                                  damage=damage, speed=bullet_speed,
                                  lifetime=bullet_range, weapon_type=weapon_type))

    def _update_anim_state(self):
        """Update animation state and facing angle based on movement or shoot target."""
        dx = self.x - self._prev_x
        dy = self.y - self._prev_y
        if abs(dx) > 0.1 or abs(dy) > 0.1:
            self.anim_state = "walk"
            if self.shoot_target is None:
                self.facing_angle = math.degrees(math.atan2(dy, dx)) + 270
        else:
            self.anim_state = "idle"
        # Face shoot target when one exists (gun points at enemy)
        if self.shoot_target is not None:
            tdx = self.shoot_target.x - self.x
            tdy = self.shoot_target.y - self.y
            self.facing_angle = math.degrees(math.atan2(tdy, tdx)) + 270
        self._prev_x = self.x
        self._prev_y = self.y

    def draw(self, camera):
        # Blink effect: skip drawing on odd 6-frame cycles during invulnerability
        if self.invulnerable_timer > 0 and (self.invulnerable_timer // 6) % 2 == 1:
            return
        sx, sy = camera.apply(self.x, self.y)

        # Shadow
        draw_shadow(screen, (sx, sy), self.RADIUS * 3, self.RADIUS * 2)

        self._update_anim_state()

        # Pick the right sprite animation
        sprite = None
        if self.anim_state == "walk" and self.sprite_walk:
            sprite = self.sprite_walk
        elif self.sprite_idle:
            sprite = self.sprite_idle

        if sprite is not None:
            sprite.update()
            frame = sprite.get_rotated_frame(self.facing_angle)
            # Apply ally fade
            if not self.is_player and self.lifetime >= 0:
                fade = max(50, int(255 * self.lifetime / self.ALLY_LIFETIME))
                frame = frame.copy()
                frame.set_alpha(fade)
            fw, fh = frame.get_size()
            screen.blit(frame, (sx - fw // 2, sy - fh // 2))
        else:
            # Fallback: simple circle
            draw_color = self.color
            if not self.is_player and self.lifetime >= 0:
                fade = max(0.2, self.lifetime / self.ALLY_LIFETIME)
                draw_color = tuple(int(c * fade) for c in self.color)
            pygame.draw.circle(screen, draw_color, (sx, sy), self.RADIUS)

        # HP bar
        bar_w = self.RADIUS * 2 + 4
        max_hp = self.max_hp
        filled = bar_w * max(0, self.hp) / max_hp
        bx = sx - bar_w // 2
        by = sy - self.RADIUS - 12
        pygame.draw.rect(screen, HEALTH_BG, (bx, by, bar_w, 4))
        pygame.draw.rect(screen, HEALTH_FG, (bx, by, int(filled), 4))
        # Lifetime bar for allies
        if not self.is_player and self.lifetime >= 0:
            life_filled = bar_w * self.lifetime / self.ALLY_LIFETIME
            by2 = sy - self.RADIUS - 17
            pygame.draw.rect(screen, HEALTH_BG, (bx, by2, bar_w, 3))
            pygame.draw.rect(screen, (100, 140, 180), (bx, by2, int(life_filled), 3))


_ENEMY_TYPE_DEFAULTS = {
    "basic":    {"hp": 3,  "speed": 1.4, "radius": 12, "color": [255, 30, 60],  "xp_value": 2},
    "runner":   {"hp": 2,  "speed": 2.2, "radius": 8,  "color": [230, 255, 0],  "xp_value": 2},
    "brute":    {"hp": 9,  "speed": 0.9, "radius": 18, "color": [255, 140, 0],  "xp_value": 5},
    "shielded": {"hp": 6,  "speed": 1.0, "radius": 14, "color": [0, 255, 255],  "xp_value": 6, "shield": True},
    "splitter": {"hp": 4,  "speed": 1.0, "radius": 14, "color": [0, 255, 100],  "xp_value": 3},
    "mini":     {"hp": 2,  "speed": 1.8, "radius": 7,  "color": [0, 255, 100],  "xp_value": 1},
    "elite":    {"hp": 15, "speed": 1.8, "radius": 16, "color": [255, 0, 255],  "xp_value": 12},
    "shooter":  {"hp": 5,  "speed": 0.8, "radius": 13, "color": [255, 100, 50], "xp_value": 5},
}


def _build_enemy_types():
    """Build ENEMY_TYPES dict from BALANCE config."""
    enemies_cfg = BALANCE.get("enemies", {})
    types = {}
    for etype, defaults in _ENEMY_TYPE_DEFAULTS.items():
        cfg = enemies_cfg.get(etype, {})
        entry = {
            "hp": cfg.get("hp", defaults["hp"]),
            "speed": cfg.get("speed", defaults["speed"]),
            "radius": cfg.get("radius", defaults["radius"]),
            "color": tuple(cfg.get("color", defaults["color"])),
            "xp_value": cfg.get("xp_value", defaults["xp_value"]),
        }
        if cfg.get("shield", defaults.get("shield", False)):
            entry["shield"] = True
        types[etype] = entry
    return types


ENEMY_TYPES = _build_enemy_types()


def _build_wave_composition():
    """Build WAVE_COMPOSITION list from BALANCE config."""
    waves_cfg = BALANCE.get("waves", {})
    comp_list = waves_cfg.get("composition", [])
    result = []
    for entry in comp_list:
        threshold = entry.get("threshold", 1)
        weights = dict(entry.get("weights", {}))
        result.append((threshold, weights))
    # Sort descending by threshold (config may already be sorted, but ensure it)
    result.sort(key=lambda x: x[0], reverse=True)
    return result


# Wave-based spawn weight tables: maps wave thresholds to enemy type weights.
# Checked in descending order; first matching threshold is used.
WAVE_COMPOSITION = _build_wave_composition()


def get_enemy_type_for_wave(wave):
    """Select a random enemy type based on the current wave's weight table."""
    for threshold, weights in WAVE_COMPOSITION:
        if wave >= threshold:
            valid = {k: v for k, v in weights.items() if k in ENEMY_TYPES}
            if not valid:
                return "basic"
            types = list(valid.keys())
            cumulative = list(valid.values())
            return random.choices(types, weights=cumulative, k=1)[0]
    return "basic"


class DeathEffect:
    """Visual-only death animation that plays once and disappears."""

    def __init__(self, x, y, facing_angle, sprite):
        self.x = x
        self.y = y
        self.facing_angle = facing_angle
        self.sprite = sprite
        self.finished = False
        self.sprite.reset()
        # Total ticks for full animation (frames * frame_speed)
        self._total_ticks = len(sprite.frames) * sprite.frame_speed
        self._tick = 0

    def update(self):
        self._tick += 1
        if self._tick >= self._total_ticks:
            self.finished = True
            # Clamp to last frame
            self.sprite.frame_index = len(self.sprite.frames) - 1
        else:
            self.sprite.update()

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        frame = self.sprite.get_rotated_frame(self.facing_angle)
        fw, fh = frame.get_size()
        screen.blit(frame, (sx - fw // 2, sy - fh // 2))


class Enemy:
    _next_id = 0

    def __init__(self, camera, enemy_type="basic", wave=1):
        Enemy._next_id += 1
        self.uid = Enemy._next_id
        self.enemy_type = enemy_type
        type_cfg = ENEMY_TYPES[enemy_type]
        scaling = BALANCE.get("enemies", {}).get("scaling", {})
        base_hp = type_cfg["hp"]
        hp_linear = scaling.get("hp_linear", 0.12)
        hp_compound = scaling.get("hp_compound", 1.06)
        hp_compound_start = scaling.get("hp_compound_start", 20)
        linear = 1 + hp_linear * (wave - 1)
        compound = hp_compound ** max(0, wave - hp_compound_start)
        self.hp = max(base_hp, int(base_hp * linear * compound))
        base_speed = type_cfg["speed"]
        speed_linear = scaling.get("speed_linear", 0.02)
        speed_cap = scaling.get("speed_cap", 2.0)
        self.speed = base_speed * min(speed_cap, 1 + speed_linear * (wave - 1))
        self.radius = type_cfg["radius"]
        self.color = type_cfg["color"]
        base_xp = type_cfg["xp_value"]
        xp_wave_divisor = scaling.get("xp_wave_divisor", 5)
        if xp_wave_divisor <= 0:
            xp_wave_divisor = 5
        self.xp_value = base_xp + wave // xp_wave_divisor
        self.shield = type_cfg.get("shield", False)
        contact_damage_divisor = scaling.get("contact_damage_divisor", 5)
        if contact_damage_divisor <= 0:
            contact_damage_divisor = 5
        self.contact_damage = 1 + (wave - 1) // contact_damage_divisor
        # Shooter-specific attributes
        shooter_cfg = BALANCE.get("enemies", {}).get("shooter_behavior", {})
        if enemy_type == "shooter":
            self.shoot_cooldown = shooter_cfg.get("shoot_cooldown", 90)
            timer_min = int(shooter_cfg.get("shoot_timer_min", 30))
            timer_max = int(shooter_cfg.get("shoot_timer_max", 90))
            if timer_min > timer_max:
                timer_min, timer_max = timer_max, timer_min
            self.shoot_timer = random.randint(timer_min, timer_max)
            self.strafe_dir = random.choice([-1, 1])
            self.approach_dist = shooter_cfg.get("approach_distance", 250)
            self.retreat_dist = shooter_cfg.get("retreat_distance", 150)
            self.firing_dist = shooter_cfg.get("firing_distance", 300)
        else:
            self.shoot_cooldown = 0
            self.shoot_timer = 0
            self.strafe_dir = 1
            self.approach_dist = 0
            self.retreat_dist = 0
            self.firing_dist = 0
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
        self.facing_angle = 0.0  # degrees
        # Load sprites
        if _assets is not None:
            self.sprite_walk = _assets.get_animation(f"enemy_{enemy_type}_walk")
            self.sprite_attack = _assets.get_animation(f"enemy_{enemy_type}_attack")
            self.sprite_death = _assets.get_animation(f"enemy_{enemy_type}_death")
        else:
            self.sprite_walk = None
            self.sprite_attack = None
            self.sprite_death = None

    def update(self, target, enemy_bullets=None):
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy) or 1
        # Track facing direction toward target
        self.facing_angle = math.degrees(math.atan2(dy, dx)) + 270
        if self.enemy_type == "shooter":
            # Distance-keeping: approach if far, retreat if close, strafe otherwise
            nx, ny = dx / dist, dy / dist
            if dist > self.approach_dist:
                # Move toward player
                self.x += nx * self.speed
                self.y += ny * self.speed
            elif dist < self.retreat_dist:
                # Retreat away from player
                self.x -= nx * self.speed
                self.y -= ny * self.speed
            else:
                # Strafe perpendicular to player (direction randomized per enemy)
                self.x += -ny * self.speed * self.strafe_dir
                self.y += nx * self.speed * self.strafe_dir
            # Clamp to map bounds after movement
            margin = 60
            self.x = max(-margin, min(MAP_WIDTH + margin, self.x))
            self.y = max(-margin, min(MAP_HEIGHT + margin, self.y))
            # Shooting logic
            self.shoot_timer = max(0, self.shoot_timer - 1)
            if self.shoot_timer <= 0 and dist <= self.firing_dist and enemy_bullets is not None:
                enemy_bullets.append(EnemyBullet(self.x, self.y, dx, dy, damage=self.contact_damage))
                self.shoot_timer = self.shoot_cooldown
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def draw(self, camera):
        sx, sy = camera.apply(self.x, self.y)
        r = self.radius

        # Shadow
        draw_shadow(screen, (sx, sy), r * 3, r * 2)

        sprite = self.sprite_walk
        if sprite is not None:
            sprite.update()
            frame = sprite.get_rotated_frame(self.facing_angle)
            fw, fh = frame.get_size()
            screen.blit(frame, (sx - fw // 2, sy - fh // 2))
        else:
            # Fallback: simple colored circle
            pygame.draw.circle(screen, self.color, (sx, sy), r)
            outline = tuple(min(255, c + 60) for c in self.color)
            pygame.draw.circle(screen, outline, (sx, sy), r, 2)

        # Draw shield ring if active
        if self.shield:
            shield_color = (80, 160, 200)
            pygame.draw.circle(screen, shield_color, (sx, sy), r + 4, 2)


class HealthPickup:
    _hp_cfg = BALANCE.get("health_pickups", {})
    RADIUS = _hp_cfg.get("radius", 8)
    LIFETIME = _hp_cfg.get("lifetime", 600)
    ATTRACT_RANGE = _hp_cfg.get("attract_range", 100)
    ATTRACT_SPEED = _hp_cfg.get("attract_speed", 4.0)
    COLLECT_RANGE = _hp_cfg.get("collect_range", 20)

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
        pickup_sprite = _assets.get_static("health_pickup") if _assets else None
        if pickup_sprite is not None:
            frame = pickup_sprite.copy()
            frame.set_alpha(int(255 * fade))
            fw, fh = frame.get_size()
            screen.blit(frame, (sx - fw // 2, sy - fh // 2))
        else:
            color = tuple(int(c * fade) for c in HEALTH_PICKUP_COLOR)
            pygame.draw.circle(screen, color, (sx, sy), self.RADIUS)
            cx_half = self.RADIUS // 2
            bright = tuple(min(255, c + 80) for c in color)
            pygame.draw.line(screen, bright, (sx - cx_half, sy), (sx + cx_half, sy), 2)
            pygame.draw.line(screen, bright, (sx, sy - cx_half), (sx, sy + cx_half), 2)


_HEALTH_DROP_DEFAULTS = {
    "basic": 0.05, "runner": 0.05, "brute": 0.12, "shielded": 0.08,
    "splitter": 0.06, "mini": 0.03, "elite": 0.15, "shooter": 0.08,
}


def _build_health_drop_chance():
    """Build HEALTH_DROP_CHANCE dict from BALANCE config."""
    drop_cfg = BALANCE.get("health_pickups", {}).get("drop_chance", {})
    return {etype: drop_cfg.get(etype, default)
            for etype, default in _HEALTH_DROP_DEFAULTS.items()}


HEALTH_DROP_CHANCE = _build_health_drop_chance()


def get_health_drop_chance(enemy_type):
    """Return the probability of dropping a health pickup for a given enemy type."""
    default_chance = BALANCE.get("health_pickups", {}).get("drop_chance", {}).get("default", 0.05)
    return HEALTH_DROP_CHANCE.get(enemy_type, default_chance)


def generate_xp_thresholds(max_level=None):
    """Generate XP thresholds for each level. Level n requires thresholds[n-1] XP."""
    xp_cfg = BALANCE.get("xp", {})
    if max_level is None:
        max_level = int(xp_cfg.get("max_level", 50))
    base = xp_cfg.get("base", 10)
    linear = xp_cfg.get("linear", 5)
    quadratic = xp_cfg.get("quadratic", 2)
    thresholds = []
    for i in range(max_level):
        thresholds.append(base + i * linear + i * i * quadratic)
    return thresholds


def check_level_up(xp, level, thresholds):
    """Check if xp >= threshold for current level. Returns (new_xp, new_level, leveled_up)."""
    if level - 1 >= len(thresholds):
        return xp, level, False
    threshold = thresholds[level - 1]
    if xp >= threshold:
        return xp - threshold, level + 1, True
    return xp, level, False


def _build_stat_upgrades():
    """Build STAT_UPGRADES list from BALANCE config."""
    ucfg = BALANCE.get("upgrades", {})
    return [
        {"name": "+Damage", "stat": "damage", "amount": ucfg.get("damage_amount", 1)},
        {"name": "+Fire Rate", "stat": "fire_rate", "amount": ucfg.get("fire_rate_amount", -3)},
        {"name": "+Bullet Speed", "stat": "bullet_speed", "amount": ucfg.get("bullet_speed_amount", 2)},
        {"name": "+Range", "stat": "range", "amount": ucfg.get("range_amount", 15)},
        {"name": "+Max HP", "stat": "max_hp", "amount": ucfg.get("max_hp_amount", 1)},
    ]


STAT_UPGRADES = _build_stat_upgrades()

_balance_initialized = True

WEAPON_TYPES = ["shotgun", "piercing", "explosive"]


def get_scaled_amount(stat, base_amount, level):
    """Scale upgrade amounts based on player level."""
    scfg = BALANCE.get("upgrades", {}).get("scaling", {})
    if stat == "damage":
        tier3_level = scfg.get("damage_tier3_level", 20)
        tier2_level = scfg.get("damage_tier2_level", 10)
        tier3_bonus = scfg.get("damage_tier3_bonus", 1)
        if level >= tier3_level:
            return base_amount + tier3_bonus
        elif level >= tier2_level:
            return base_amount
    elif stat == "fire_rate":
        tier2_level = scfg.get("fire_rate_tier2_level", 15)
        tier2_bonus = scfg.get("fire_rate_tier2_bonus", -2)
        if level >= tier2_level:
            return base_amount + tier2_bonus
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
    scfg = BALANCE.get("upgrades", {}).get("scaling", {})
    milestone_threshold = scfg.get("milestone_threshold", 15)
    milestone_interval_late = scfg.get("milestone_interval_late", 4)
    milestone_interval_early = scfg.get("milestone_interval_early", 5)
    milestone_interval = milestone_interval_late if level > milestone_threshold else milestone_interval_early
    if milestone_interval <= 0:
        milestone_interval = 5
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
    min_fire_rate = BALANCE.get("upgrades", {}).get("min_fire_rate", 5)
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
        new_weapon["fire_rate"] = max(min_fire_rate, new_weapon["fire_rate"])
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
                ws["fire_rate"] = max(min_fire_rate, ws["fire_rate"])
    return weapon_stats


def find_closest_enemy(unit, enemies):
    best, best_d = None, float('inf')
    for e in enemies:
        d = math.hypot(e.x - unit.x, e.y - unit.y)
        if d < best_d:
            best, best_d = e, d
    return best


def draw_grid(camera):
    """Draw tiled ground background and map border."""
    if _tile_renderer is not None:
        _tile_renderer.draw(screen, camera)
    else:
        # Fallback: solid fill
        screen.fill(BG)
    # Draw map border
    bx, by = camera.apply(0, 0)
    bw, bh = MAP_WIDTH, MAP_HEIGHT
    pygame.draw.rect(screen, (60, 45, 30), (bx - 2, by - 2, bw + 4, bh + 4), 5)
    pygame.draw.rect(screen, BORDER_COLOR, (bx, by, bw, bh), 3)


HUD_MARGIN = 10  # Spacing from screen edges for all HUD widgets


def draw_hud_panel(x, y, w, h, border_color=BORDER_COLOR):
    """Draw a semi-transparent rounded-rect HUD panel."""
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
    "shotgun": (220, 140, 40),
    "piercing": (140, 200, 220),
    "explosive": (220, 80, 40),
}


def draw_hud_stats(score, wave, allies, bomb_parts=0):
    """Draw top-right stats widget: score, wave counter, squad size, bomb parts."""
    hud_font, hud_font_small = _get_hud_fonts()

    panel_w, panel_h = 180, 100
    panel_x = WIDTH - panel_w - HUD_MARGIN
    panel_y = HUD_MARGIN
    draw_hud_panel(panel_x, panel_y, panel_w, panel_h)

    pad = 10
    tx = panel_x + pad
    right_x = panel_x + panel_w - pad

    # Score
    score_label = hud_font_small.render("Score", True, BORDER_COLOR)
    screen.blit(score_label, (tx, panel_y + 6))
    score_val = hud_font.render(str(score), True, PLAYER_COLOR)
    screen.blit(score_val, (right_x - score_val.get_width(), panel_y + 4))

    # Wave
    wave_label = hud_font_small.render("Wave", True, BORDER_COLOR)
    screen.blit(wave_label, (tx, panel_y + 26))
    wave_val = hud_font.render(str(wave), True, PLAYER_COLOR)
    screen.blit(wave_val, (right_x - wave_val.get_width(), panel_y + 24))

    # Squad size
    squad_label = hud_font_small.render("Squad", True, BORDER_COLOR)
    screen.blit(squad_label, (tx, panel_y + 46))
    squad_count = 1 + len(allies)
    squad_val = hud_font.render(str(squad_count), True, PLAYER_COLOR)
    screen.blit(squad_val, (right_x - squad_val.get_width(), panel_y + 44))

    # Bomb parts
    parts_label = hud_font_small.render("Bomb", True, BORDER_COLOR)
    screen.blit(parts_label, (tx, panel_y + 66))
    parts_color = (50, 200, 50) if bomb_parts >= BOMB_PARTS_TOTAL else PLAYER_COLOR
    parts_val = hud_font.render(f"{bomb_parts}/{BOMB_PARTS_TOTAL}", True, parts_color)
    screen.blit(parts_val, (right_x - parts_val.get_width(), panel_y + 64))


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
                    escape_rooms=None, escape_flash_timer=0,
                    enemy_bullets=None, explosion_effects=None,
                    death_effects=None, bomb_parts=0):
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
    if enemy_bullets:
        for eb in enemy_bullets:
            if _is_visible(camera, eb.x, eb.y):
                eb.draw(camera)
    for e in enemies:
        if _is_visible(camera, e.x, e.y):
            e.draw(camera)
    if death_effects:
        for de in death_effects:
            if _is_visible(camera, de.x, de.y):
                de.draw(camera)
    if health_pickups:
        for hp_pickup in health_pickups:
            if _is_visible(camera, hp_pickup.x, hp_pickup.y):
                hp_pickup.draw(camera)
    if heal_effects:
        for hx, hy, ht in heal_effects:
            if _is_visible(camera, hx, hy):
                sx, sy = camera.apply(hx, hy)
                alpha_frac = ht / 15
                r = int(10 + 10 * (1 - alpha_frac))
                heal_surf = _get_glow_surface((r * 2, r * 2))
                heal_surf.fill((0, 0, 0, 0))
                alpha = int(120 * alpha_frac)
                pygame.draw.circle(heal_surf, (180, 40, 40, alpha), (r, r), r)
                screen.blit(heal_surf, (sx - r, sy - r))
    # Explosion area-of-effect indicators
    if explosion_effects:
        for ex, ey, et, e_radius in explosion_effects:
            if _is_visible(camera, ex, ey, margin=e_radius + 20):
                sx, sy = camera.apply(ex, ey)
                frac = et / 20  # 20 frames total
                # Ring expanding outward as time passes
                ring_r = int(e_radius * (0.3 + 0.7 * (1.0 - frac)))
                alpha = max(10, int(200 * frac))
                dim = (e_radius + 10) * 2
                expl_surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
                center = dim // 2
                # Filled circle (warm orange, semi-transparent)
                pygame.draw.circle(expl_surf, (255, 140, 30, alpha // 2), (center, center), ring_r)
                # Outer ring (bright)
                pygame.draw.circle(expl_surf, (255, 200, 50, alpha), (center, center), ring_r, 3)
                screen.blit(expl_surf, (sx - center, sy - center))
    for a in allies:
        if _is_visible(camera, a.x, a.y):
            a.draw(camera)
    player.draw(camera)

    # Escape room flash effect
    if escape_flash_timer > 0:
        flash_surface = _get_glow_surface((WIDTH, HEIGHT))
        flash_surface.fill((0, 0, 0, 0))
        alpha = int(140 * (escape_flash_timer / 15))
        flash_surface.fill((50, 180, 50, alpha))
        screen.blit(flash_surface, (0, 0))

    # HUD - Top-left vitals widget
    draw_hud_vitals(player, xp, xp_thresholds, level)

    # HUD - Top-right stats widget
    draw_hud_stats(score, wave, allies, bomb_parts=bomb_parts)

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


# Upgrade panel constants (card-based layout)
PANEL_BG_COLOR = (20, 18, 15, 200)
CARD_GAP = 20  # pixels between cards
CARD_MARGIN = 30  # left/right margin around all cards
CARD_TITLE_AREA = 70  # vertical space above cards for "Level N!" title
CARD_HOVER_SCALE = 1.08  # scale multiplier for hovered card

# Card asset globals (populated by _load_card_assets after pygame init)
_card_surface = None  # original upgrades_card.png surface
_card_toml = None  # parsed TOML positions dict
_card_scaled_surface = None  # pre-scaled card surface for rendering
_card_scale_factor = 1.0  # scale factor applied to cards
_card_scaled_positions = None  # TOML positions scaled for rendering
ICON_TARGET_SIZE = 180  # icon area diameter on original 405px-wide card
_upgrade_icon_cache = {}  # category -> scaled pygame.Surface
_card_hover_surface = None  # pre-scaled hover card surface
PANEL_WIDTH = 500  # updated by _load_card_assets
PANEL_HEIGHT = 350  # updated by _load_card_assets


def _load_card_assets():
    """Load card background image and TOML config, compute layout constants."""
    global _card_surface, _card_toml, _card_scaled_surface, _card_scale_factor
    global _card_scaled_positions, PANEL_WIDTH, PANEL_HEIGHT, _card_hover_surface

    # Clear stale icon cache (icons depend on scale factor)
    _upgrade_icon_cache.clear()

    # Load card background image
    card_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "upgrades", "upgrades_card.png")
    _card_surface = pygame.image.load(card_path).convert_alpha()

    # Parse TOML config
    toml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "upgrades", "upgrades_card.toml")
    with open(toml_path, "rb") as f:
        _card_toml = tomllib.load(f)

    # Card dimensions from loaded image
    card_w = _card_surface.get_width()
    card_h = _card_surface.get_height()

    # Calculate scale factor: 3 cards + gaps + margins must fit in screen width
    available_width = WIDTH - 2 * CARD_MARGIN
    target_card_width = (available_width - 2 * CARD_GAP) / 3
    _card_scale_factor = target_card_width / card_w

    # Pre-scale card surface
    scaled_w = int(card_w * _card_scale_factor)
    scaled_h = int(card_h * _card_scale_factor)
    _card_scaled_surface = pygame.transform.smoothscale(_card_surface, (scaled_w, scaled_h))

    # Pre-scale TOML positions
    _card_scaled_positions = {}
    for key in ("icon", "title", "body", "level"):
        _card_scaled_positions[key] = (
            int(_card_toml[key]["x"] * _card_scale_factor),
            int(_card_toml[key]["y"] * _card_scale_factor),
        )

    # Update panel dimensions
    PANEL_WIDTH = 3 * scaled_w + 2 * CARD_GAP + 2 * CARD_MARGIN
    PANEL_HEIGHT = scaled_h + CARD_TITLE_AREA + CARD_MARGIN

    # Pre-compute hover-scaled card surface
    hover_w = int(scaled_w * CARD_HOVER_SCALE)
    hover_h = int(scaled_h * CARD_HOVER_SCALE)
    _card_hover_surface = pygame.transform.smoothscale(_card_surface, (hover_w, hover_h))


def create_upgrade_icon(option):
    """Load and return a scaled icon surface for an upgrade option.

    Loads the PNG from assets/upgrades/upgrades_{category}.png, scales it to
    fit the icon area on the card, and caches the result.  Returns a transparent
    surface for unknown categories.
    """
    cat = option.get("category", "")

    if cat in _upgrade_icon_cache:
        return _upgrade_icon_cache[cat]

    # Compute the target pixel size for the icon on the scaled card
    scaled_icon_size = int(ICON_TARGET_SIZE * _card_scale_factor)
    if scaled_icon_size < 1:
        scaled_icon_size = 1

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "upgrades", f"upgrades_{cat}.png")
    if os.path.isfile(icon_path):
        raw = pygame.image.load(icon_path)
        try:
            raw = raw.convert_alpha()
        except pygame.error:
            pass  # no display surface yet (e.g. in tests)
        surf = pygame.transform.smoothscale(raw, (scaled_icon_size, scaled_icon_size))
    else:
        surf = pygame.Surface((scaled_icon_size, scaled_icon_size), pygame.SRCALPHA)

    _upgrade_icon_cache[cat] = surf
    return surf


def _panel_origin():
    """Return (x, y) for the centered upgrade panel."""
    return (WIDTH - PANEL_WIDTH) // 2, (HEIGHT - PANEL_HEIGHT) // 2


def draw_upgrade_panel(level, upgrade_options):
    """Draw a card-based upgrade selector with 3 cards side by side."""
    if _card_scaled_surface is None:
        return
    panel_x, panel_y = _panel_origin()

    # "Level N!" title centered above the cards
    title = title_font.render(f"Level {level}!", True, (200, 160, 80))
    title_shadow = title_font.render(f"Level {level}!", True, (50, 35, 15))
    tx = panel_x + PANEL_WIDTH // 2 - title.get_width() // 2
    ty = panel_y + 10
    screen.blit(title_shadow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))

    hud_font, hud_font_small = _get_hud_fonts()

    # Card dimensions from the pre-scaled surface
    card_w = _card_scaled_surface.get_width()
    card_h = _card_scaled_surface.get_height()

    for i, opt in enumerate(upgrade_options):
        # Card x position: margin + i * (card_w + gap)
        base_card_x = panel_x + CARD_MARGIN + i * (card_w + CARD_GAP)
        base_card_y = panel_y + CARD_TITLE_AREA

        # Determine if this card is hovered
        is_hovered = (i == level_up_selected_index)

        if is_hovered:
            # Use pre-computed hover-scaled card surface
            hover_w = _card_hover_surface.get_width()
            hover_h = _card_hover_surface.get_height()
            # Offset so the scaled card stays centered in its slot
            card_x = base_card_x - (hover_w - card_w) // 2
            card_y = base_card_y - (hover_h - card_h) // 2
            screen.blit(_card_hover_surface, (card_x, card_y))
            # Scale factor for positioning elements on the hovered card
            h_scale = CARD_HOVER_SCALE
        else:
            card_x = base_card_x
            card_y = base_card_y
            screen.blit(_card_scaled_surface, (card_x, card_y))
            h_scale = 1.0

        # Icon centered at scaled icon position
        icon = opt.get('_icon') or create_upgrade_icon(opt)
        icon_cx, icon_cy = _card_scaled_positions["icon"]
        if is_hovered:
            # Scale icon for hover
            hover_icon_w = int(icon.get_width() * CARD_HOVER_SCALE)
            hover_icon_h = int(icon.get_height() * CARD_HOVER_SCALE)
            icon = pygame.transform.smoothscale(icon, (hover_icon_w, hover_icon_h))
            icon_bx = card_x + int(icon_cx * h_scale) - icon.get_width() // 2
            icon_by = card_y + int(icon_cy * h_scale) - icon.get_height() // 2
        else:
            icon_bx = card_x + icon_cx - icon.get_width() // 2
            icon_by = card_y + icon_cy - icon.get_height() // 2
        screen.blit(icon, (icon_bx, icon_by))

        # Title text centered at scaled title position
        name_text = opt.get("name", "")
        name_surf = font.render(name_text, True, (200, 160, 80))
        title_cx, title_cy = _card_scaled_positions["title"]
        screen.blit(name_surf, (card_x + int(title_cx * h_scale) - name_surf.get_width() // 2,
                                card_y + int(title_cy * h_scale) - name_surf.get_height() // 2))

        # Body: description text centered at scaled body position
        cur_lv = opt.get("current_level", 0)
        is_unlock = opt.get("is_unlock", False)
        cat_key = opt.get("category", "")
        cat_info = UPGRADE_CATEGORIES.get(cat_key)

        body_cx, body_cy = _card_scaled_positions["body"]

        if cat_info:
            desc_text = cat_info["description"]
        else:
            desc_text = ""
        desc_surf = hud_font_small.render(desc_text, True, (180, 160, 120))
        screen.blit(desc_surf, (card_x + int(body_cx * h_scale) - desc_surf.get_width() // 2,
                                card_y + int(body_cy * h_scale) - desc_surf.get_height() // 2 - 10))

        # New value in green below description
        if cat_info and not is_unlock:
            cur_val = cat_info["format_value"](cur_lv)
            next_val = cat_info["format_value"](cur_lv + 1)
            val_text = f"{cur_val} -> {next_val}"
            val_surf = hud_font_small.render(val_text, True, (80, 200, 80))
            screen.blit(val_surf, (card_x + int(body_cx * h_scale) - val_surf.get_width() // 2,
                                   card_y + int(body_cy * h_scale) - val_surf.get_height() // 2 + 12))

        # Level text centered at scaled level position
        level_cx, level_cy = _card_scaled_positions["level"]
        if is_unlock:
            lv_text = "UNLOCK"
            lv_color = (80, 200, 80)
        else:
            lv_text = f"LEVEL {cur_lv + 1}"
            lv_color = (200, 160, 80)
        lv_surf = font.render(lv_text, True, lv_color)
        screen.blit(lv_surf, (card_x + int(level_cx * h_scale) - lv_surf.get_width() // 2,
                              card_y + int(level_cy * h_scale) - lv_surf.get_height() // 2))


def get_hovered_upgrade_index(mouse_x, mouse_y, num_options):
    """Return the index of the upgrade card under the mouse, or -1 if none."""
    if num_options <= 0 or _card_scaled_surface is None:
        return -1
    panel_x, panel_y = _panel_origin()
    card_w = _card_scaled_surface.get_width()
    card_h = _card_scaled_surface.get_height()
    for i in range(num_options):
        card_x = panel_x + CARD_MARGIN + i * (card_w + CARD_GAP)
        card_y = panel_y + CARD_TITLE_AREA
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
        if card_rect.collidepoint(mouse_x, mouse_y):
            return i
    return -1


def apply_resolution():
    """Apply the current resolution and fullscreen settings."""
    global screen, WIDTH, HEIGHT, options_fullscreen, _menu_background, _fade_overlay, _dim_overlay
    # Fullscreen always uses native desktop resolution
    if options_fullscreen and _native_resolution:
        WIDTH, HEIGHT = _native_resolution
    else:
        res = SUPPORTED_RESOLUTIONS[options_resolution_index]
        WIDTH, HEIGHT = res
    flags = pygame.FULLSCREEN | pygame.SCALED if options_fullscreen else pygame.SCALED
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except pygame.error:
        # Fallback to windowed mode if fullscreen fails
        options_fullscreen = False
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
    _menu_background = None
    _fade_overlay = None
    _dim_overlay = None
    if _card_surface is not None and pygame.display.get_surface() is not None:
        _load_card_assets()
    # Reload UI backgrounds at new resolution
    if _assets is not None:
        from assets_manager import ASSET_CONFIG
        _assets.load_static("ui_background", ASSET_CONFIG["ui_background"], (WIDTH, HEIGHT))
        _assets.load_static("ui_background2", ASSET_CONFIG["ui_background2"], (WIDTH, HEIGHT))
    save_settings()


def draw_options_menu():
    """Draw the options menu matching main menu visual style."""
    global _menu_background

    # Draw background image or solid fallback
    bg = _assets.get_static("ui_background") if _assets else None
    if bg is not None:
        screen.blit(bg, (0, 0))
    else:
        screen.fill(BG)

    # Title in upper-left area matching main menu style
    options_start_y = MENU_START_Y
    title = title_font.render("Options", True, (200, 60, 40))
    title_shadow = title_font.render("Options", True, (40, 15, 10))
    tx = MENU_X
    ty = options_start_y - 120
    screen.blit(title_shadow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))

    if options_fullscreen:
        res_label = f"{_native_resolution[0]}x{_native_resolution[1]} (native)" if _native_resolution else "Native"
    else:
        res_label = (f"{SUPPORTED_RESOLUTIONS[options_resolution_index][0]}x"
                     f"{SUPPORTED_RESOLUTIONS[options_resolution_index][1]}")
    items = [
        ("Resolution", res_label),
        ("Fullscreen", "On" if options_fullscreen else "Off"),
        ("Reset Profile", ""),
        ("Back", ""),
    ]

    ticks = pygame.time.get_ticks()

    for i, (label, value) in enumerate(items):
        y = options_start_y + i * MENU_ITEM_HEIGHT
        is_selected = (i == options_selected_index)
        x = MENU_X + (MENU_HOVER_INDENT if is_selected else 0)

        if is_selected:
            text_color = (255, 220, 160)
            shadow_surf = menu_font.render(label, True, (80, 40, 10))
            screen.blit(shadow_surf, (x + 1, y + 1))
        else:
            text_color = (180, 170, 160)

        text_surf = menu_font.render(label, True, text_color)
        screen.blit(text_surf, (x, y))

        if value:
            val_color = PLAYER_COLOR if is_selected else (180, 170, 160)
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
    for i in range(4):  # Resolution, Fullscreen, Reset Profile, Back
        if get_menu_item_rect(i).collidepoint(mx, my):
            return i
    return -1


def draw_menu_separator(surface, x, y, width, ticks):
    """Draw a subtle separator line between menu items."""
    color = (100, 70, 40)
    pygame.draw.line(surface, color, (x, y), (x + width, y), 1)


def draw_menu():
    global _menu_background, menu_fade_alpha, menu_fade_active

    # Draw background image or solid fallback
    bg = _assets.get_static("ui_background") if _assets else None
    if bg is not None:
        screen.blit(bg, (0, 0))
    else:
        screen.fill(BG)

    # Title in upper-left area — blood red zombie style
    title = title_font.render("SBU: Nuclear Option", True, (200, 60, 40))
    title_shadow = title_font.render("SBU: Nuclear Option", True, (40, 15, 10))
    tx = MENU_X
    ty = MENU_START_Y - 120
    screen.blit(title_shadow, (tx + 2, ty + 2))
    screen.blit(title, (tx, ty))

    ticks = pygame.time.get_ticks()

    # Draw menu items
    for i, item_text in enumerate(MENU_ITEMS):
        y = MENU_START_Y + i * MENU_ITEM_HEIGHT
        is_selected = (i == menu_selected_index)
        x = MENU_X + (MENU_HOVER_INDENT if is_selected else 0)

        if is_selected:
            text_color = (255, 220, 160)
            shadow_surf = menu_font.render(item_text, True, (80, 40, 10))
            screen.blit(shadow_surf, (x + 1, y + 1))
        else:
            text_color = (180, 170, 160)

        text_surf = menu_font.render(item_text, True, text_color)
        screen.blit(text_surf, (x, y))

        # Draw separator line after each item except the last
        if i < len(MENU_ITEMS) - 1:
            sep_y = y + MENU_ITEM_HEIGHT - 10
            draw_menu_separator(screen, MENU_X, sep_y, 200, ticks)

    # Profile summary — show saved upgrades in bottom-right
    try:
        _menu_profile = load_profile()
        upgrades = _menu_profile.get("upgrades", {})
        total_upgrades = sum(upgrades.values())
        if total_upgrades > 0:
            hud_font, hud_font_small = _get_hud_fonts()
            runs = _menu_profile.get("total_runs", 0)
            best = _menu_profile.get("best_wave", 0)
            # Summary line
            summary = hud_font_small.render(
                f"Profile: {total_upgrades} upgrades | {runs} runs | Best wave: {best}",
                True, (140, 130, 110))
            screen.blit(summary, (MENU_X, HEIGHT - 60))
            # Active upgrades
            active = [f"{UPGRADE_CATEGORIES[k]['name']} Lv{v}"
                      for k, v in upgrades.items() if v > 0]
            if active:
                line = hud_font_small.render(
                    "  ".join(active[:6]), True, (120, 110, 90))
                screen.blit(line, (MENU_X, HEIGHT - 38))
    except Exception:
        pass

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


def draw_game_over(score, level=1, killer_info=None):
    # Semi-transparent dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    # GAME OVER in blood red with shadow
    t1 = title_font.render("GAME OVER", True, (180, 30, 20))
    t1_shadow = title_font.render("GAME OVER", True, (40, 8, 5))
    tx = WIDTH // 2 - t1.get_width() // 2
    ty = HEIGHT // 4
    screen.blit(t1_shadow, (tx + 2, ty + 2))
    screen.blit(t1, (tx, ty))
    # Killed by info
    info_y = ty + t1.get_height() + 30
    text_color = (200, 180, 160)
    if killer_info:
        kb = font.render(f"Killed by: {killer_info['killed_by']}", True, (220, 100, 80))
        screen.blit(kb, (WIDTH // 2 - kb.get_width() // 2, info_y))
        info_y += 35
        wt = font.render(f"Wave: {killer_info['wave']}", True, text_color)
        screen.blit(wt, (WIDTH // 2 - wt.get_width() // 2, info_y))
        info_y += 30
        st = font.render(f"Survived: {killer_info['survival_time']}s", True, text_color)
        screen.blit(st, (WIDTH // 2 - st.get_width() // 2, info_y))
        info_y += 30
    t2 = font.render(f"Score: {score}   Level: {level}", True, text_color)
    screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, info_y + 10))
    t3 = font.render("Press ENTER to Restart", True, (180, 160, 120))
    screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, info_y + 50))
    pygame.display.flip()


def draw_death_review(data):
    """Draw the death review screen showing earned upgrades and saved upgrade."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    hud_font, hud_font_small = _get_hud_fonts()

    # Title
    t1 = title_font.render("RUN COMPLETE", True, (200, 160, 80))
    t1_shadow = title_font.render("RUN COMPLETE", True, (50, 35, 15))
    tx = WIDTH // 2 - t1.get_width() // 2
    screen.blit(t1_shadow, (tx + 2, 22))
    screen.blit(t1, (tx, 20))

    # Stats line
    ki = data.get("killer_info", {})
    stats_text = f"Wave {data.get('wave', 0)}  |  Score {data.get('score', 0)}  |  Level {data.get('level', 1)}"
    st = font.render(stats_text, True, (180, 160, 130))
    screen.blit(st, (WIDTH // 2 - st.get_width() // 2, 80))

    # Upgrade list
    earned = data.get("earned", [])
    saved_idx = data.get("saved_idx", -1)
    scroll = data.get("scroll_offset", 0)

    card_h = 40
    list_top = 130
    list_bottom = HEIGHT - 80
    visible_h = list_bottom - list_top
    max_scroll = max(0, len(earned) * card_h - visible_h)
    scroll = max(0, min(scroll, max_scroll))
    data["scroll_offset"] = scroll

    # Clip region for the list
    clip_surf = pygame.Surface((WIDTH - 80, visible_h), pygame.SRCALPHA)
    clip_surf.fill((0, 0, 0, 0))

    for i, upg in enumerate(earned):
        card_y = i * card_h - scroll
        if card_y + card_h < 0 or card_y > visible_h:
            continue

        is_saved = (i == saved_idx)
        card_x = 20

        # Card background
        if is_saved:
            bg_color = (60, 50, 20, 180)
            border_color = (220, 180, 50)
        else:
            bg_color = (30, 28, 25, 120)
            border_color = (80, 70, 50)

        card_rect = pygame.Rect(card_x, card_y, WIDTH - 120, card_h - 4)
        card_bg = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
        card_bg.fill(bg_color)
        clip_surf.blit(card_bg, card_rect.topleft)
        pygame.draw.rect(clip_surf, border_color, card_rect, 1, border_radius=3)

        # Category name and level
        name = upg.get("name", "?")
        from_lv = upg.get("from_level", 0)
        to_lv = upg.get("to_level", 1)

        if is_saved:
            label_color = (255, 220, 100)
            badge = hud_font_small.render("SAVED", True, (255, 200, 50))
            clip_surf.blit(badge, (card_rect.right - badge.get_width() - 8, card_y + 10))
        else:
            label_color = (180, 170, 150)

        is_unlock = from_lv == 0 and upg.get("category", "") in ("weapon_shotgun", "weapon_piercing", "weapon_explosive")
        if is_unlock:
            text = hud_font.render(f"UNLOCK {name}", True, (80, 200, 80))
        else:
            text = hud_font.render(f"{name}  Lv {from_lv} -> {to_lv}", True, label_color)
        clip_surf.blit(text, (card_x + 10, card_y + 8))

    screen.blit(clip_surf, (40, list_top))

    # Scroll indicator
    if max_scroll > 0:
        scroll_frac = scroll / max_scroll if max_scroll > 0 else 0
        bar_h = max(20, int(visible_h * visible_h / (len(earned) * card_h)))
        bar_y = list_top + int((visible_h - bar_h) * scroll_frac)
        pygame.draw.rect(screen, (100, 90, 70), (WIDTH - 35, bar_y, 6, bar_h), border_radius=3)

    # Footer
    footer = font.render("Press ENTER to continue", True, (180, 160, 120))
    screen.blit(footer, (WIDTH // 2 - footer.get_width() // 2, HEIGHT - 50))
    pygame.display.flip()


def _wrap_text(text, font_obj, max_width):
    """Split text into lines that fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font_obj.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_intro_screen():
    """Draw the mission briefing intro screen with commander portrait."""
    screen.fill((10, 8, 5))
    hud_font, hud_font_small = _get_hud_fonts()

    # Commander portrait on the left
    commander = _assets.get_static("commander_icon") if _assets else None
    portrait_x = 60
    portrait_y = HEIGHT // 2 - 100
    if commander:
        screen.blit(commander, (portrait_x, portrait_y))
        # Border around portrait
        pygame.draw.rect(screen, (100, 80, 40),
                         (portrait_x - 2, portrait_y - 2, 132, 132), 2)

    # Title
    title = title_font.render("MISSION BRIEFING", True, (200, 60, 40))
    title_shadow = title_font.render("MISSION BRIEFING", True, (40, 15, 10))
    tx = 220
    screen.blit(title_shadow, (tx + 2, 42))
    screen.blit(title, (tx, 40))

    # Commander label
    cmd_label = hud_font_small.render("Gen. Kovalenko", True, (160, 140, 100))
    if commander:
        screen.blit(cmd_label, (portrait_x + 64 - cmd_label.get_width() // 2, portrait_y + 136))

    # Story text
    story = (
        "Colonel Vinnyk, the situation is critical. "
        "SBU operation to deliver a nuclear device to moscow has been compromised. "
        "russian air defense shot down our transport plane over the combat zone. "
        "The bomb broke apart on impact - 10 components are now scattered across "
        "hostile territory swarming with russian zomboids. "
        "Our scientists are working to triangulate the location of each component. "
        "As they identify positions, coordinates will be relayed to you directly. "
        "Arm yourself, gather supplies, and recruit any surviving locals. "
        "The mission to destroy moscow must not fail. "
        "Slava Ukraini, Colonel. Do not let us down."
    )

    text_x = 220
    text_y = 110
    max_w = WIDTH - text_x - 60
    lines = _wrap_text(story, font, max_w)
    for line in lines:
        surf = font.render(line, True, (200, 190, 170))
        screen.blit(surf, (text_x, text_y))
        text_y += 32

    # Objectives
    obj_y = text_y + 30
    obj_title = font.render("OBJECTIVES:", True, (220, 180, 80))
    screen.blit(obj_title, (text_x, obj_y))
    obj_y += 35
    objectives = [
        "Recover all 10 nuclear bomb components",
        "Eliminate russian zomboids",
        "Recruit local survivors to your squad",
        "Complete the mission at all costs",
    ]
    for obj in objectives:
        dot = hud_font_small.render(f"  > {obj}", True, (180, 170, 150))
        screen.blit(dot, (text_x, obj_y))
        obj_y += 26

    # Footer
    footer = font.render("Press ENTER to begin mission", True, (180, 160, 120))
    screen.blit(footer, (WIDTH // 2 - footer.get_width() // 2, HEIGHT - 60))
    pygame.display.flip()


def draw_victory_screen(score, bomb_parts, killer_count):
    """Draw the victory screen after collecting all bomb parts."""
    screen.fill((10, 8, 5))
    hud_font, hud_font_small = _get_hud_fonts()

    # Commander portrait
    commander = _assets.get_static("commander_icon") if _assets else None
    portrait_x = 60
    portrait_y = HEIGHT // 2 - 100
    if commander:
        screen.blit(commander, (portrait_x, portrait_y))
        pygame.draw.rect(screen, (50, 180, 50),
                         (portrait_x - 2, portrait_y - 2, 132, 132), 2)

    # Title
    title = title_font.render("MISSION COMPLETE", True, (50, 200, 50))
    title_shadow = title_font.render("MISSION COMPLETE", True, (10, 40, 10))
    tx = 220
    screen.blit(title_shadow, (tx + 2, 42))
    screen.blit(title, (tx, 40))

    # Commander label
    cmd_label = hud_font_small.render("Gen. Kovalenko", True, (100, 160, 100))
    if commander:
        screen.blit(cmd_label, (portrait_x + 64 - cmd_label.get_width() // 2, portrait_y + 136))

    # Victory text
    victory = (
        f"Colonel Vinnyk, outstanding work. All {bomb_parts} components of the "
        "nuclear device have been recovered and reassembled. "
        f"During the operation you eliminated {killer_count} russian zomboids. "
        "The bomb is being loaded onto a drone and deployed to moscow as we speak. "
        "The kremlin will be nothing but a glowing crater by morning. "
        "Ukraine will remember your sacrifice, Colonel. "
        "Slava Ukraini. Heroiam Slava."
    )

    text_x = 220
    text_y = 110
    max_w = WIDTH - text_x - 60
    lines = _wrap_text(victory, font, max_w)
    for line in lines:
        surf = font.render(line, True, (200, 190, 170))
        screen.blit(surf, (text_x, text_y))
        text_y += 32

    # Stats
    stat_y = text_y + 30
    stats = [
        f"Bomb parts collected: {bomb_parts}/{BOMB_PARTS_TOTAL}",
        f"Zomboids eliminated: {killer_count}",
    ]
    for s in stats:
        surf = font.render(s, True, (220, 180, 80))
        screen.blit(surf, (text_x, stat_y))
        stat_y += 35

    # Footer
    footer = font.render("Press ENTER to return to base", True, (180, 160, 120))
    screen.blit(footer, (WIDTH // 2 - footer.get_width() // 2, HEIGHT - 60))
    pygame.display.flip()


def run():
    global options_selected_index, options_resolution_index, options_fullscreen
    global menu_selected_index, active_joystick
    global level_up_selected_index, _gamepad_nav_last_time, _last_levelup_mouse_pos
    global _current_music
    init_pygame()
    _current_music = None
    state = STATE_MENU
    _play_music("menu.wav")
    camera = Camera()
    player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
    obstacles = []
    escape_rooms = []
    allies = []
    enemies = []
    bullets = []
    enemy_bullets = []
    health_pickups = []
    heal_effects = []
    explosion_effects = []
    death_effects = []
    escape_flash_timer = 0
    score = 0
    spawn_timer = 0
    waves_cfg = BALANCE.get("waves", {})
    spawn_interval = waves_cfg.get("spawn_interval_base", 110)
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
    last_damage_source = ""
    killer_info = {}
    # Roguelite progression variables
    profile = default_profile()
    game_vars = {"ally_spawn_chance": 0.10, "heal_restore_amount": 1, "player_speed": 3.5}
    run_upgrade_levels = dict(profile["upgrades"])
    profile_start_levels = dict(profile["upgrades"])
    death_review_data = None
    bomb_parts_collected = 0

    def reset_game():
        nonlocal camera, player, obstacles, escape_rooms, allies, enemies
        nonlocal bullets, enemy_bullets, health_pickups, heal_effects, explosion_effects, death_effects, score
        nonlocal spawn_timer, spawn_interval, wave, wave_timer
        nonlocal xp, level, weapon_inventory, upgrade_options, escape_flash_timer
        nonlocal run_stats, run_start_time, total_xp_earned
        nonlocal last_damage_source, killer_info
        nonlocal run_upgrade_levels, profile_start_levels, game_vars, profile
        nonlocal bomb_parts_collected
        camera = Camera()
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        obstacles = generate_obstacles()
        er = EscapeRoom(0, 0)
        er.relocate(obstacles)
        escape_rooms = [er]
        allies = []
        enemies = []
        bullets = []
        enemy_bullets = []
        health_pickups = []
        heal_effects = []
        explosion_effects = []
        death_effects = []
        escape_flash_timer = 0
        score = 0
        spawn_timer = 0
        spawn_interval = BALANCE.get("waves", {}).get("spawn_interval_base", 110)
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
        last_damage_source = ""
        killer_info = {}
        bomb_parts_collected = 0
        # Roguelite: load profile and apply saved upgrades
        profile = load_profile()
        game_vars = apply_profile_to_game(profile, player, weapon_inventory)
        run_upgrade_levels = dict(profile["upgrades"])
        profile_start_levels = dict(profile["upgrades"])

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
        prog_apply_upgrade(opt, run_upgrade_levels, weapon_inventory, player, game_vars)
        cat = opt.get("category", "")
        if cat.startswith("weapon_"):
            wt = cat.replace("weapon_", "")
            if wt == "normal":
                wt = "normal"
            run_stats["weapons_used"].add(wt)
            run_stats["weapon_picks"][wt] = run_stats["weapon_picks"].get(wt, 0) + 1
        run_stats["level_logs"].append({
            "level": level,
            "wave": wave,
            "time": round(time.time() - run_start_time, 1),
            "chosen": opt.get("name", "?"),
            "options": [o.get("name", "?") for o in upgrade_options],
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
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_INTRO:
                        state = STATE_PLAYING
                        _play_music("game.wav")
                    elif state == STATE_VICTORY:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_PLAYING:
                        save_if_playing()
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_DEATH_REVIEW:
                        state = STATE_GAME_OVER
                    elif state == STATE_GAME_OVER:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_LEVEL_UP:
                        save_if_playing()
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_MENU:
                        running = False
                elif state == STATE_OPTIONS:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        options_selected_index = (options_selected_index - 1) % 4
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        options_selected_index = (options_selected_index + 1) % 4
                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                        if options_selected_index == 0 and not options_fullscreen:
                            options_resolution_index = (
                                options_resolution_index + direction
                            ) % len(SUPPORTED_RESOLUTIONS)
                            apply_resolution()
                        elif options_selected_index == 1:
                            options_fullscreen = not options_fullscreen
                            apply_resolution()
                    elif event.key == pygame.K_RETURN:
                        if options_selected_index == 2:  # Reset Profile
                            save_profile(default_profile())
                        elif options_selected_index == 3:  # Back
                            state = STATE_MENU
                            _play_music("menu.wav")
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
                            state = STATE_INTRO
                        elif menu_selected_index == 1:  # OPTIONS
                            options_selected_index = 0
                            state = STATE_OPTIONS
                        elif menu_selected_index == 2:  # QUIT
                            running = False
                elif event.key == pygame.K_RETURN:
                    if state == STATE_INTRO:
                        state = STATE_PLAYING
                        _play_music("game.wav")
                    elif state == STATE_VICTORY:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_DEATH_REVIEW:
                        state = STATE_GAME_OVER
                    elif state == STATE_GAME_OVER:
                        reset_game()
                        state = STATE_PLAYING
                        _play_music("game.wav")
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
                            state = STATE_INTRO
                        elif menu_selected_index == 1:  # OPTIONS
                            options_selected_index = 0
                            state = STATE_OPTIONS
                        elif menu_selected_index == 2:  # QUIT
                            running = False
                    elif state == STATE_OPTIONS:
                        if options_selected_index == 0 and not options_fullscreen:
                            options_resolution_index = (
                                options_resolution_index + 1
                            ) % len(SUPPORTED_RESOLUTIONS)
                            apply_resolution()
                        elif options_selected_index == 1:  # Fullscreen - toggle
                            options_fullscreen = not options_fullscreen
                            apply_resolution()
                        elif options_selected_index == 2:  # Reset Profile
                            save_profile(default_profile())
                        elif options_selected_index == 3:  # Back
                            state = STATE_MENU
                            _play_music("menu.wav")
                            _reset_menu_state()
                    elif state == STATE_LEVEL_UP and upgrade_options:
                        if 0 <= level_up_selected_index < len(upgrade_options):
                            apply_chosen_upgrade(upgrade_options[level_up_selected_index])
                    elif state == STATE_INTRO:
                        state = STATE_PLAYING
                        _play_music("game.wav")
                    elif state == STATE_VICTORY:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_DEATH_REVIEW:
                        state = STATE_GAME_OVER
                    elif state == STATE_GAME_OVER:
                        reset_game()
                        state = STATE_PLAYING
                        _play_music("game.wav")
                elif event.button == 1:  # B button - back/escape
                    if state == STATE_DEATH_REVIEW:
                        state = STATE_GAME_OVER
                    elif state == STATE_OPTIONS:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_LEVEL_UP:
                        save_if_playing()
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_PLAYING:
                        save_if_playing()
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_GAME_OVER:
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                    elif state == STATE_MENU:
                        running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == STATE_OPTIONS:
                    idx = get_hovered_options_index(event.pos[0], event.pos[1])
                    if idx == 0 and not options_fullscreen:  # Resolution - cycle (windowed only)
                        options_resolution_index = (
                            options_resolution_index + 1
                        ) % len(SUPPORTED_RESOLUTIONS)
                        apply_resolution()
                    elif idx == 1:  # Fullscreen - toggle
                        options_fullscreen = not options_fullscreen
                        apply_resolution()
                    elif idx == 2:  # Reset Profile
                        save_profile(default_profile())
                    elif idx == 3:  # Back
                        state = STATE_MENU
                        _play_music("menu.wav")
                        _reset_menu_state()
                elif state == STATE_MENU:
                    idx = get_hovered_menu_index(event.pos[0], event.pos[1])
                    if idx == 0:  # NEW GAME
                        reset_game()
                        state = STATE_INTRO
                    elif idx == 1:  # OPTIONS
                        options_selected_index = 0
                        state = STATE_OPTIONS
                    elif idx == 2:  # QUIT
                        running = False
                elif state == STATE_LEVEL_UP and upgrade_options:
                    idx = get_hovered_upgrade_index(event.pos[0], event.pos[1], len(upgrade_options))
                    if 0 <= idx < len(upgrade_options):
                        apply_chosen_upgrade(upgrade_options[idx])
                elif state == STATE_INTRO:
                    state = STATE_PLAYING
                    _play_music("game.wav")
                elif state == STATE_VICTORY:
                    state = STATE_MENU
                    _play_music("menu.wav")
                    _reset_menu_state()
                elif state == STATE_DEATH_REVIEW:
                    state = STATE_GAME_OVER
            # Mouse scroll for death review
            if event.type == pygame.MOUSEBUTTONDOWN and state == STATE_DEATH_REVIEW and death_review_data:
                if event.button == 4:  # scroll up
                    death_review_data["scroll_offset"] = max(0, death_review_data["scroll_offset"] - 30)
                elif event.button == 5:  # scroll down
                    death_review_data["scroll_offset"] += 30

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
                        if current_options_idx == 0 and not options_fullscreen:
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

        if state == STATE_INTRO:
            draw_intro_screen()
            clock.tick(FPS)
            continue

        if state == STATE_VICTORY:
            draw_victory_screen(score, bomb_parts_collected, score)
            clock.tick(FPS)
            continue

        if state == STATE_DEATH_REVIEW:
            draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                            score, wave, level, weapon_inventory, xp, xp_thresholds,
                            health_pickups, heal_effects, escape_rooms,
                            escape_flash_timer, enemy_bullets=enemy_bullets,
                            explosion_effects=explosion_effects,
                            death_effects=death_effects,
                            bomb_parts=bomb_parts_collected)
            if death_review_data:
                draw_death_review(death_review_data)
            clock.tick(FPS)
            continue

        if state == STATE_GAME_OVER:
            draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                            score, wave, level, weapon_inventory, xp, xp_thresholds,
                            health_pickups, heal_effects, escape_rooms,
                            escape_flash_timer, enemy_bullets=enemy_bullets,
                            explosion_effects=explosion_effects,
                            death_effects=death_effects,
                            bomb_parts=bomb_parts_collected)
            draw_game_over(score, level, killer_info=killer_info)
            clock.tick(FPS)
            continue

        if state == STATE_LEVEL_UP:
            draw_game_scene(camera, obstacles, bullets, enemies, allies, player,
                            score, wave, level, weapon_inventory, xp, xp_thresholds,
                            health_pickups, heal_effects, escape_rooms,
                            escape_flash_timer, enemy_bullets=enemy_bullets,
                            explosion_effects=explosion_effects,
                            death_effects=death_effects,
                            bomb_parts=bomb_parts_collected)
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
            player.x += mx / length * player.player_speed
            player.y += my / length * player.player_speed
            player.x = max(player.RADIUS, min(MAP_WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(MAP_HEIGHT - player.RADIUS, player.y))
            for obs in obstacles:
                player.x, player.y = obs.push_circle_out(player.x, player.y, player.RADIUS)
            player.x = max(player.RADIUS, min(MAP_WIDTH - player.RADIUS, player.x))
            player.y = max(player.RADIUS, min(MAP_HEIGHT - player.RADIUS, player.y))

        # Update camera
        camera.update(player)

        # Check bomb part (escape room) collection
        for er in escape_rooms:
            if er.collides_circle(player.x, player.y, player.RADIUS):
                bomb_parts_collected += 1
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
                    upgrade_options = gen_upgrade_options(run_upgrade_levels)
                    for opt in upgrade_options:
                        opt['_icon'] = create_upgrade_icon(opt)
                    level_up_selected_index = 0
                    _last_levelup_mouse_pos = pygame.mouse.get_pos()
                    state = STATE_LEVEL_UP
                # Health pickup drops
                for dx, dy, etype in er_dead:
                    if random.random() < get_health_drop_chance(etype):
                        health_pickups.append(HealthPickup(dx, dy, heal_amount=game_vars["heal_restore_amount"]))
                # Ally spawns
                for _ in range(er_killed):
                    if random.random() < game_vars["ally_spawn_chance"]:
                        color = random.choice(ALLY_COLORS)
                        a = Unit(player.x + random.uniform(-30, 30),
                                 player.y + random.uniform(-30, 30), color)
                        allies.append(a)
                # Clear all enemy bullets
                enemy_bullets = []
                # Check victory condition
                if bomb_parts_collected >= BOMB_PARTS_TOTAL:
                    state = STATE_VICTORY
                    break
                er.relocate(obstacles, escape_rooms)
                escape_flash_timer = 15
                break

        # If escape room triggered a level-up, skip rest of frame
        if state == STATE_LEVEL_UP:
            draw_game_scene(
                camera, obstacles, bullets, enemies, allies,
                player, score, wave, level, weapon_inventory,
                xp, xp_thresholds, health_pickups,
                heal_effects, escape_rooms, escape_flash_timer,
                enemy_bullets=enemy_bullets,
                explosion_effects=explosion_effects,
                death_effects=death_effects,
                bomb_parts=bomb_parts_collected)
            draw_dim_overlay()
            draw_upgrade_panel(level, upgrade_options)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # Spawn enemies
        spawn_timer += 1
        wave_timer += 1
        wave_timer_limit = BALANCE.get("waves", {}).get("timer", 480)
        if wave_timer > wave_timer_limit:
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
            spawn_min = BALANCE.get("waves", {}).get("spawn_interval_min", 10)
            spawn_reduction = BALANCE.get("waves", {}).get("spawn_interval_reduction", 14)
            spawn_interval = max(spawn_min, spawn_interval - spawn_reduction)
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
                u.shoot_target = target
                u.shoot_at(target, bullets, weapon_stats=ws)
            else:
                u.shoot_target = None

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

        # Update enemy bullets
        for eb in enemy_bullets:
            eb.update()
        for eb in enemy_bullets:
            for obs in obstacles:
                if obs.collides_circle(eb.x, eb.y, eb.RADIUS):
                    eb.life = 0
                    break
        enemy_bullets = [eb for eb in enemy_bullets if eb.life > 0 and
                         -50 <= eb.x <= MAP_WIDTH + 50 and -50 <= eb.y <= MAP_HEIGHT + 50]

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
                        if e.sprite_death:
                            death_effects.append(DeathEffect(e.x, e.y, e.facing_angle, e.sprite_death))
                        run_stats["weapon_kills"][wt] = run_stats["weapon_kills"].get(wt, 0) + 1
                        run_stats["wave_kills"] += 1
                        if e.enemy_type == "splitter":
                            split_spawns.append((e.x, e.y))
                    break
            if not hit:
                new_enemies.append(e)
        enemies = new_enemies

        # Explosive area damage (skip enemies already hit directly by the bullet)
        EXPLOSIVE_RADIUS = BALANCE.get("weapons", {}).get("explosive", {}).get("radius", 60)
        for ex, ey, edmg, direct_hit_uid in explosive_hits:
            # Spawn visual explosion effect (x, y, timer, radius)
            explosion_effects.append((ex, ey, 20, EXPLOSIVE_RADIUS))
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
                            if e.sprite_death:
                                death_effects.append(DeathEffect(e.x, e.y, e.facing_angle, e.sprite_death))
                            run_stats["weapon_kills"]["explosive"] = run_stats["weapon_kills"].get("explosive", 0) + 1
                            run_stats["wave_kills"] += 1
                            if e.enemy_type == "splitter":
                                split_spawns.append((e.x, e.y))
                            continue
                surviving_after_explosion.append(e)
            enemies = surviving_after_explosion
        # Spawn mini enemies from dead splitters
        splitter_cfg = BALANCE.get("splitter", {})
        mini_count = int(splitter_cfg.get("mini_count", 2))
        spawn_offset = splitter_cfg.get("spawn_offset", 12)
        for sx, sy in split_spawns:
            for i in range(mini_count):
                if len(enemies) >= get_max_enemies(wave):
                    break
                mini = Enemy(camera, enemy_type="mini", wave=wave)
                if mini_count <= 1:
                    mini.x = sx
                else:
                    mini.x = sx + spawn_offset * (2 * i / (mini_count - 1) - 1)
                mini.y = sy
                enemies.append(mini)

        score += killed

        # Spawn health pickups from dead enemies
        for dx, dy, etype in dead_enemies:
            if random.random() < get_health_drop_chance(etype):
                health_pickups.append(HealthPickup(dx, dy, heal_amount=game_vars["heal_restore_amount"]))

        # Award XP and check level-up
        total_xp_earned += xp_earned
        run_stats["wave_xp_earned"] += xp_earned
        xp += xp_earned
        xp, level, leveled_up = check_level_up(xp, level, xp_thresholds)
        if leveled_up:
            upgrade_options = gen_upgrade_options(run_upgrade_levels)
            for opt in upgrade_options:
                opt['_icon'] = create_upgrade_icon(opt)
            level_up_selected_index = 0
            _last_levelup_mouse_pos = pygame.mouse.get_pos()
            state = STATE_LEVEL_UP
            # Spawn allies before pausing (reward kills even on level-up frame)
            for _ in range(killed):
                if random.random() < game_vars["ally_spawn_chance"]:
                    color = random.choice(ALLY_COLORS)
                    a = Unit(player.x + random.uniform(-30, 30),
                             player.y + random.uniform(-30, 30), color)
                    allies.append(a)
            # Skip enemy movement and collision to prevent death during level-up
            clock.tick(FPS)
            continue

        # Spawn allies for kills (1-in-10 chance per kill)
        for _ in range(killed):
            if random.random() < game_vars["ally_spawn_chance"]:
                color = random.choice(ALLY_COLORS)
                a = Unit(player.x + random.uniform(-30, 30),
                         player.y + random.uniform(-30, 30), color)
                allies.append(a)

        # Update enemies
        for e in enemies:
            e.update(player, enemy_bullets)
            for obs in obstacles:
                e.x, e.y = obs.push_circle_out(e.x, e.y, e.radius)
            for er in escape_rooms:
                e.x, e.y = er.push_circle_out(e.x, e.y, e.radius)

        # Enemy-player collision (damage player)
        invuln_duration = Unit.INVULNERABLE_DURATION
        surviving = []
        for e in enemies:
            if player.hp > 0 and math.hypot(e.x - player.x, e.y - player.y) < e.radius + player.RADIUS:
                if player.invulnerable_timer <= 0:
                    player.hp -= e.contact_damage
                    run_stats["damage_taken"] += e.contact_damage
                    run_stats["wave_damage_taken"] += e.contact_damage
                    player.invulnerable_timer = invuln_duration
                    last_damage_source = e.enemy_type
                # Enemy is destroyed on contact regardless of invulnerability
            else:
                surviving.append(e)
        enemies = surviving

        # Enemy bullet-player collision
        if player.hp > 0:
            surviving_eb = []
            for eb in enemy_bullets:
                if math.hypot(eb.x - player.x, eb.y - player.y) < eb.RADIUS + player.RADIUS:
                    if player.invulnerable_timer <= 0:
                        player.hp -= eb.damage
                        run_stats["damage_taken"] += eb.damage
                        run_stats["wave_damage_taken"] += eb.damage
                        player.invulnerable_timer = invuln_duration
                        last_damage_source = "Enemy Bullet"
                    # Bullet is consumed on contact regardless of invulnerability
                else:
                    surviving_eb.append(eb)
            enemy_bullets = surviving_eb

        # Decrement invulnerability timer (after collision checks)
        if player.invulnerable_timer > 0:
            player.invulnerable_timer -= 1

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
        # Update explosion effects (countdown timer)
        explosion_effects = [(x, y, t - 1, r) for x, y, t, r in explosion_effects if t > 0]
        # Update death animations
        for de in death_effects:
            de.update()
        death_effects = [de for de in death_effects if not de.finished]

        if player.hp <= 0:
            player.invulnerable_timer = 0
            survival_time = time.time() - run_start_time
            killer_info = {
                "killed_by": last_damage_source or "Unknown",
                "wave": wave,
                "survival_time": round(survival_time, 1),
            }
            run_data = collect_run_stats(
                run_stats, score, level, wave, total_xp_earned,
                survival_time, weapon_inventory)
            save_stats(run_data)
            # Roguelite: compute earned upgrades and save one to profile
            earned = compute_run_earned_upgrades(profile_start_levels, run_upgrade_levels)
            saved_idx, saved_upgrade = select_saved_upgrade(earned, profile) if earned else (None, None)
            if saved_upgrade is not None:
                save_run_upgrade_to_profile(profile, saved_upgrade, wave=wave)
                death_review_data = {
                    "earned": earned,
                    "saved_idx": saved_idx,
                    "saved_upgrade": saved_upgrade,
                    "score": score,
                    "wave": wave,
                    "level": level,
                    "killer_info": killer_info,
                    "scroll_offset": 0,
                }
                state = STATE_DEATH_REVIEW
            else:
                profile["total_runs"] = profile.get("total_runs", 0) + 1
                save_profile(profile)
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
                        escape_rooms, escape_flash_timer,
                        enemy_bullets=enemy_bullets,
                        explosion_effects=explosion_effects,
                        death_effects=death_effects,
                        bomb_parts=bomb_parts_collected)

        pygame.display.flip()
        clock.tick(FPS)

    _stop_music()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
