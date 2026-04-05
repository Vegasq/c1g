"""Asset loading, sprite animation, and tile rendering for Squad Survivors.

Provides:
- AnimatedSprite: frame-based animation with rotation caching
- AssetManager: singleton that loads/caches all game sprites
- TileRenderer: procedural tiled ground backgrounds (fallback)
- TiledMapRenderer: loads Tiled (.tmx) maps via pytmx
"""

import os
import math
import random
import pygame

# ---------------------------------------------------------------------------
# Base path for all assets (relative to this file)
# ---------------------------------------------------------------------------
_ASSETS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ---------------------------------------------------------------------------
# Asset path configuration — maps logical names to folder/file paths
# ---------------------------------------------------------------------------
_CHAR_BASE = os.path.join(
    "zombie-tds-main-characters", "Characters",
    "PNG_Bodyparts&Animations", "PNG Animations",
)
_ZOMBIE_BASE = os.path.join(
    "tds-zombie-character-sprite", "Zombies", "PNG Animations",
)
_MONSTER_BASE = os.path.join(
    "tds-monster-character-sprites", "Monsters", "PNG Animations",
)
_TILE_BASE = os.path.join(
    "zombie-tds-tilesets-soil-stones-plants-water-destroyed-cars",
)
_BUILDING_BASE = os.path.join(
    "zombie-tds-tilesets-buildings-and-furniture",
)
_UI_BASE = os.path.join(
    "zombie-tds-game-user-interface", "PNG",
)

ASSET_CONFIG = {
    # Player (Man)
    "player_idle": os.path.join(_CHAR_BASE, "Man", "Idle_gun"),
    "player_walk": os.path.join(_CHAR_BASE, "Man", "Walk_gun"),
    "player_shoot": os.path.join(_CHAR_BASE, "Man", "Gun_Shot"),
    "player_death": os.path.join(_CHAR_BASE, "Man", "Death"),

    # Allies (Girl)
    "ally_idle": os.path.join(_CHAR_BASE, "Girl", "Idle_gun"),
    "ally_walk": os.path.join(_CHAR_BASE, "Girl", "Walk_gun"),

    # Enemies — 1LVL zombies
    "enemy_basic_walk": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie3_male", "Walk"),
    "enemy_basic_attack": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie3_male", "Attack"),
    "enemy_runner_walk": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie1_female", "Walk"),
    "enemy_runner_attack": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie1_female", "Attack"),
    "enemy_mini_walk": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie2_female", "Walk"),

    # Enemies — 2LVL zombies
    "enemy_shielded_walk": os.path.join(_ZOMBIE_BASE, "2LVL", "Army_zombie", "Walk"),
    "enemy_shielded_attack": os.path.join(_ZOMBIE_BASE, "2LVL", "Army_zombie", "Attack"),
    "enemy_splitter_walk": os.path.join(_ZOMBIE_BASE, "2LVL", "Cop_Zombie", "Walk"),

    # Enemies — 3LVL monsters
    "enemy_brute_walk": os.path.join(_MONSTER_BASE, "3LVL", "Zombie_big_hands", "Walk"),
    "enemy_brute_attack": os.path.join(_MONSTER_BASE, "3LVL", "Zombie_big_hands", "Attack1"),
    "enemy_shooter_walk": os.path.join(_MONSTER_BASE, "3LVL", "Zpmbie_big_head", "Walk"),

    # Enemies — 4LVL bosses
    "enemy_elite_walk": os.path.join(_MONSTER_BASE, "4LVL", "Boss1", "Walk"),
    "enemy_elite_attack": os.path.join(_MONSTER_BASE, "4LVL", "Boss1", "Attack_1"),

    # Enemy death animations
    "enemy_basic_death": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie3_male", "Death"),
    "enemy_runner_death": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie1_female", "Death"),
    "enemy_mini_death": os.path.join(_ZOMBIE_BASE, "1LVL", "Zombie2_female", "Death"),
    "enemy_shielded_death": os.path.join(_ZOMBIE_BASE, "2LVL", "Army_zombie", "Death"),
    "enemy_splitter_death": os.path.join(_ZOMBIE_BASE, "2LVL", "Cop_Zombie", "Death"),
    "enemy_brute_death": os.path.join(_MONSTER_BASE, "3LVL", "Zombie_big_hands", "Death"),
    "enemy_shooter_death": os.path.join(_MONSTER_BASE, "3LVL", "Zpmbie_big_head", "Death"),
    "enemy_elite_death": os.path.join(_MONSTER_BASE, "4LVL", "Boss1", "Death"),

    # Tiles
    "tile_grass": os.path.join(_TILE_BASE, "Tiles&Details", "PNG", "Grass_tiles"),
    "tile_ground": os.path.join(_TILE_BASE, "Tiles&Details", "PNG", "Ground_tiles"),
    "tile_asphalt": os.path.join(_TILE_BASE, "Tiles&Details", "PNG", "Asphalt_tiles"),

    # Objects for obstacles — outside objects (rocks, logs, trees, helicopter)
    "obstacle_outside": os.path.join(_TILE_BASE, "Objects", "PNG", "Objects_outside"),

    # Destroyed vehicles — specific assembled sprites
    "vehicle_car": os.path.join("zombie-tds-machines-and-tanks", "PNG", "Car", "car_0004_Layer-5.png"),
    "vehicle_tank": os.path.join("zombie-tds-machines-and-tanks", "PNG", "Tank", "tank_0013_Layer-0.png"),
    "vehicle_armored": os.path.join("zombie-tds-machines-and-tanks", "PNG", "Armored_car", "armored_car_0010_Layer-0.png"),
    "vehicle_pickup": os.path.join("zombie-tds-machines-and-tanks", "PNG", "Pickup", "pickup_0004_Layer-5.png"),
    "vehicle_compact_tank": os.path.join("zombie-tds-machines-and-tanks", "PNG", "Compact_tank", "pickup_0004_Layer-5.png"),

    # Items
    "health_pickup": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0005_health.png"),
    "item_gun": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0000_gun.png"),
    "item_speed": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0006_speed.png"),
    "item_armor": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0010_armor.png"),
    "item_fire": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0001_fire.png"),
    "item_superpower": os.path.join(
        "zombie-tds-main-characters", "Items", "PNG", "items_0008_superpower.png"),

    # UI
    "ui_background": os.path.join(_UI_BASE, "background.png"),
    "ui_background2": os.path.join(_UI_BASE, "background2.png"),
}

# Number of quantized rotation angles (16 = every 22.5 degrees)
_ROTATION_STEPS = 16
_ANGLE_STEP = 360.0 / _ROTATION_STEPS


def _quantize_angle(degrees):
    """Round angle to nearest quantized step."""
    return round(degrees / _ANGLE_STEP) * _ANGLE_STEP


# ---------------------------------------------------------------------------
# AnimatedSprite
# ---------------------------------------------------------------------------
class AnimatedSprite:
    """Frame-based sprite animation with rotation caching."""

    def __init__(self, frames, frame_speed=6):
        """
        Args:
            frames: list of pygame.Surface (pre-scaled, convert_alpha'd)
            frame_speed: ticks between frame advances
        """
        self.frames = frames
        self.frame_speed = max(1, frame_speed)
        self.frame_index = 0
        self.tick_counter = 0
        self._rotation_cache = {}

    def update(self):
        """Advance animation by one tick."""
        self.tick_counter += 1
        if self.tick_counter >= self.frame_speed:
            self.tick_counter = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def get_frame(self):
        """Return current animation frame."""
        return self.frames[self.frame_index]

    def get_rotated_frame(self, angle_degrees):
        """Return current frame rotated to given angle, with caching.

        Args:
            angle_degrees: rotation in degrees (0 = up/default sprite orientation)
        """
        q_angle = _quantize_angle(angle_degrees)
        key = (self.frame_index, q_angle)
        cached = self._rotation_cache.get(key)
        if cached is not None:
            return cached
        # Limit cache size
        if len(self._rotation_cache) > _ROTATION_STEPS * len(self.frames) * 2:
            self._rotation_cache.clear()
        frame = self.frames[self.frame_index]
        # pygame rotates counter-clockwise; negate for clockwise
        rotated = pygame.transform.rotate(frame, -q_angle)
        self._rotation_cache[key] = rotated
        return rotated

    def reset(self):
        """Reset animation to first frame."""
        self.frame_index = 0
        self.tick_counter = 0

    def clone(self):
        """Create a new AnimatedSprite sharing the same frame surfaces but with independent state."""
        sprite = AnimatedSprite(self.frames, self.frame_speed)
        sprite._rotation_cache = self._rotation_cache  # share cache
        return sprite


# ---------------------------------------------------------------------------
# AssetManager
# ---------------------------------------------------------------------------
class AssetManager:
    """Singleton that loads and caches all game assets."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._animations = {}   # name -> AnimatedSprite (template)
        self._statics = {}      # name -> pygame.Surface
        self._tile_surfaces = {}  # name -> list[pygame.Surface]
        self._obstacle_surfaces = []  # list of pygame.Surface for obstacles

    @staticmethod
    def reset():
        """Reset the singleton (for testing)."""
        AssetManager._instance = None

    def _abs_path(self, rel_path):
        """Resolve a relative asset path to absolute."""
        return os.path.join(_ASSETS_ROOT, rel_path)

    def _load_image(self, path, target_size=None):
        """Load a single image, optionally scale it. Returns Surface or fallback."""
        try:
            surf = pygame.image.load(path)
            if surf.get_alpha() is not None or path.lower().endswith(".png"):
                surf = surf.convert_alpha()
            else:
                surf = surf.convert()
            if target_size:
                surf = pygame.transform.smoothscale(surf, target_size)
            return surf
        except (pygame.error, FileNotFoundError, OSError):
            # Fallback: colored rectangle
            size = target_size or (32, 32)
            fallback = pygame.Surface(size, pygame.SRCALPHA)
            fallback.fill((200, 50, 200, 180))  # magenta = missing asset
            return fallback

    def load_animation(self, name, folder_rel, target_size, frame_speed=6):
        """Load all PNGs from a folder as an animation.

        Args:
            name: logical name for this animation
            folder_rel: path relative to assets root
            target_size: (width, height) to scale each frame
            frame_speed: ticks between frame advances
        """
        folder = self._abs_path(folder_rel)
        frames = []
        if os.path.isdir(folder):
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith(".png")
            )
            for fname in files:
                surf = self._load_image(os.path.join(folder, fname), target_size)
                frames.append(surf)
        if not frames:
            # Fallback: single frame
            fallback = pygame.Surface(target_size, pygame.SRCALPHA)
            fallback.fill((200, 50, 200, 180))
            frames = [fallback]
        sprite = AnimatedSprite(frames, frame_speed)
        self._animations[name] = sprite
        return sprite

    def load_static(self, name, file_rel, target_size=None):
        """Load a single static image.

        Args:
            name: logical name
            file_rel: path relative to assets root
            target_size: optional (width, height) to scale
        """
        path = self._abs_path(file_rel)
        surf = self._load_image(path, target_size)
        self._statics[name] = surf
        return surf

    def load_tile_set(self, name, folder_rel, tile_size):
        """Load all PNGs from a folder as tile variants.

        Args:
            name: logical name for this tile set
            folder_rel: path relative to assets root
            tile_size: (width, height) to scale each tile
        """
        folder = self._abs_path(folder_rel)
        tiles = []
        if os.path.isdir(folder):
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith(".png")
            )
            for fname in files:
                surf = self._load_image(os.path.join(folder, fname), tile_size)
                tiles.append(surf)
        if not tiles:
            fallback = pygame.Surface(tile_size)
            fallback.fill((40, 35, 25))
            tiles = [fallback]
        self._tile_surfaces[name] = tiles
        return tiles

    def load_obstacle_set(self, folder_rel, max_count=20):
        """Load obstacle sprites from a folder (random subset).

        Args:
            folder_rel: path relative to assets root
            max_count: maximum number of obstacle sprites to load
        """
        folder = self._abs_path(folder_rel)
        surfaces = []
        if os.path.isdir(folder):
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith(".png")
            )
            # Take a selection of obstacle sprites
            for fname in files[:max_count]:
                surf = self._load_image(os.path.join(folder, fname))
                surfaces.append(surf)
        return surfaces

    def get_animation(self, name):
        """Get a cloned AnimatedSprite by name (independent animation state)."""
        template = self._animations.get(name)
        if template is None:
            return None
        return template.clone()

    def get_static(self, name):
        """Get a static surface by name."""
        return self._statics.get(name)

    def get_tiles(self, name):
        """Get tile surface list by name."""
        return self._tile_surfaces.get(name, [])

    def preload_all(self, screen_size=(1024, 768)):
        """Load all game assets. Call after pygame display is created."""
        # Player animations — scale to ~40px tall (visible at game scale)
        player_h = 40
        player_w = int(player_h * 0.7)
        player_size = (player_w, player_h)
        self.load_animation("player_idle", ASSET_CONFIG["player_idle"], player_size, frame_speed=8)
        self.load_animation("player_walk", ASSET_CONFIG["player_walk"], player_size, frame_speed=5)
        self.load_animation("player_shoot", ASSET_CONFIG["player_shoot"], player_size, frame_speed=4)
        self.load_animation("player_death", ASSET_CONFIG["player_death"], player_size, frame_speed=6)

        # Ally animations (Girl) — same size as player
        self.load_animation("ally_idle", ASSET_CONFIG["ally_idle"], player_size, frame_speed=8)
        self.load_animation("ally_walk", ASSET_CONFIG["ally_walk"], player_size, frame_speed=5)

        # Enemy animations — sized relative to their game radius
        enemy_sizes = {
            "basic": (30, 36),
            "runner": (22, 26),
            "brute": (48, 56),
            "shielded": (36, 42),
            "splitter": (36, 42),
            "mini": (18, 22),
            "elite": (44, 52),
            "shooter": (34, 40),
        }
        for etype, size in enemy_sizes.items():
            walk_key = f"enemy_{etype}_walk"
            if walk_key in ASSET_CONFIG:
                self.load_animation(walk_key, ASSET_CONFIG[walk_key], size, frame_speed=5)
            attack_key = f"enemy_{etype}_attack"
            if attack_key in ASSET_CONFIG:
                self.load_animation(attack_key, ASSET_CONFIG[attack_key], size, frame_speed=4)
            death_key = f"enemy_{etype}_death"
            if death_key in ASSET_CONFIG:
                self.load_animation(death_key, ASSET_CONFIG[death_key], size, frame_speed=5)

        # Tiles — 128x128 matching game grid
        tile_size = (128, 128)
        self.load_tile_set("grass", ASSET_CONFIG["tile_grass"], tile_size)
        self.load_tile_set("ground", ASSET_CONFIG["tile_ground"], tile_size)

        # Health pickup
        self.load_static("health_pickup", ASSET_CONFIG["health_pickup"], (20, 20))

        # Item icons for upgrade panel (32x32)
        icon_size = (32, 32)
        for item_name in ("item_gun", "item_speed", "item_armor", "item_fire", "item_superpower"):
            if item_name in ASSET_CONFIG:
                self.load_static(item_name, ASSET_CONFIG[item_name], icon_size)

        # Obstacle sprites — destroyed vehicles + outside objects (rocks, logs, trees)
        vehicles = []
        for vkey in ("vehicle_car", "vehicle_tank", "vehicle_armored",
                     "vehicle_pickup", "vehicle_compact_tank"):
            vehicles.append(self._load_image(self._abs_path(ASSET_CONFIG[vkey])))
        outside_surfs = self.load_obstacle_set(ASSET_CONFIG["obstacle_outside"], max_count=25)
        self._obstacle_surfaces = vehicles + outside_surfs

        # UI backgrounds
        self.load_static("ui_background", ASSET_CONFIG["ui_background"], screen_size)
        self.load_static("ui_background2", ASSET_CONFIG["ui_background2"], screen_size)

    def get_random_obstacle_sprite(self, width, height, seed=0):
        """Get a random obstacle sprite scaled to fit the given dimensions."""
        if not self._obstacle_surfaces:
            fallback = pygame.Surface((width, height), pygame.SRCALPHA)
            fallback.fill((60, 50, 40, 220))
            return fallback
        rng = random.Random(seed)
        surf = rng.choice(self._obstacle_surfaces)
        return pygame.transform.smoothscale(surf, (width, height))


# ---------------------------------------------------------------------------
# TileRenderer
# ---------------------------------------------------------------------------
class TileRenderer:
    """Renders a tiled ground background using loaded tile assets."""

    def __init__(self, map_width, map_height, tile_size=128, seed=42):
        self.map_width = map_width
        self.map_height = map_height
        self.tile_size = tile_size
        self.cols = math.ceil(map_width / tile_size)
        self.rows = math.ceil(map_height / tile_size)
        self._tile_map = None
        self._seed = seed

    def build(self, grass_tiles, ground_tiles):
        """Assign tile variants to each grid cell.

        Only uses the center/fill tile (index 0) from each set — the other
        12 tiles are edge/corner transition pieces meant for autotiling.

        Args:
            grass_tiles: list of pygame.Surface (grass variants)
            ground_tiles: list of pygame.Surface (ground/dirt variants)
        """
        rng = random.Random(self._seed)
        # Only use center/fill tiles (index 0) — seamless, no edges
        fill_tiles = []
        if grass_tiles:
            fill_tiles.append(grass_tiles[0])
        if ground_tiles:
            fill_tiles.append(ground_tiles[0])
        if not fill_tiles:
            fallback = pygame.Surface((self.tile_size, self.tile_size))
            fallback.fill((40, 35, 25))
            fill_tiles = [fallback]

        self._tile_map = []
        for row in range(self.rows):
            row_tiles = []
            for col in range(self.cols):
                tile = rng.choice(fill_tiles)
                row_tiles.append(tile)
            self._tile_map.append(row_tiles)

    def draw(self, screen, camera):
        """Blit only the visible tiles onto the screen."""
        if self._tile_map is None:
            return
        ts = self.tile_size
        # Compute visible tile range
        start_col = max(0, int(camera.x // ts))
        start_row = max(0, int(camera.y // ts))
        screen_w = screen.get_width()
        screen_h = screen.get_height()
        end_col = min(self.cols, int((camera.x + screen_w) // ts) + 2)
        end_row = min(self.rows, int((camera.y + screen_h) // ts) + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_surf = self._tile_map[row][col]
                sx = int(col * ts - camera.x)
                sy = int(row * ts - camera.y)
                screen.blit(tile_surf, (sx, sy))


# ---------------------------------------------------------------------------
# TiledMapRenderer — loads Tiled (.tmx) maps via pytmx
# ---------------------------------------------------------------------------
class TiledMapRenderer:
    """Renders a Tiled (.tmx) map using pytmx.

    Supports multiple layers, proper terrain transitions, and tile scaling.
    Falls back gracefully if pytmx is not installed.
    """

    def __init__(self, tmx_path, target_tile_size=128):
        try:
            from pytmx.util_pygame import load_pygame
        except ImportError:
            raise ImportError("pytmx is required for .tmx map loading. Install with: pip install pytmx")
        self.tmx_data = load_pygame(tmx_path)
        self.target_tile_size = target_tile_size
        self.map_pixel_w = self.tmx_data.width * target_tile_size
        self.map_pixel_h = self.tmx_data.height * target_tile_size
        # Pre-scale cache: (original_surface_id, target_size) -> scaled_surface
        self._scale_cache = {}

    def _get_scaled(self, image):
        """Return image scaled to target tile size, with caching."""
        ts = self.target_tile_size
        target = (ts, ts)
        if image.get_size() == target:
            return image
        key = id(image)
        cached = self._scale_cache.get(key)
        if cached is not None:
            return cached
        scaled = pygame.transform.smoothscale(image, target)
        self._scale_cache[key] = scaled
        return scaled

    def draw(self, screen, camera):
        """Blit visible tiles from all visible layers."""
        ts = self.target_tile_size
        screen_w = screen.get_width()
        screen_h = screen.get_height()

        for layer in self.tmx_data.visible_layers:
            if not hasattr(layer, 'tiles'):
                continue
            for x, y, image in layer.tiles():
                px = x * ts - int(camera.x)
                py = y * ts - int(camera.y)
                # Cull off-screen tiles
                if px > screen_w or px < -ts or py > screen_h or py < -ts:
                    continue
                scaled = self._get_scaled(image)
                screen.blit(scaled, (px, py))
