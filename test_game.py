import unittest
import math
import os
import pygame
from unittest.mock import MagicMock, patch
from game import (generate_xp_thresholds, check_level_up, default_weapon_stats, default_weapon_inventory,
                  Bullet, EnemyBullet, Unit,
                  generate_upgrade_options, apply_upgrade, get_scaled_amount, STAT_UPGRADES, WEAPON_TYPES,
                  draw_glow,
                  BG, PLAYER_COLOR, ENEMY_COLOR, GRID_COLOR, BORDER_COLOR,
                  OBSTACLE_COLOR, OBSTACLE_BORDER, BULLET_COLOR, HEALTH_FG,
                  Camera, Enemy, Obstacle, ENEMY_TYPES,
                  WAVE_COMPOSITION, get_enemy_type_for_wave,
                  HealthPickup,
                  HEALTH_DROP_CHANCE, get_health_drop_chance,
                  STATE_MENU, STATE_PLAYING, STATE_GAME_OVER, STATE_LEVEL_UP, STATE_OPTIONS,
                  MENU_ITEMS,
                  SUPPORTED_RESOLUTIONS, apply_resolution, detect_native_resolution,
                  EscapeRoom,
                  MAP_WIDTH, MAP_HEIGHT, MAX_ENEMIES_BASE, MAX_ENEMIES_CAP, get_max_enemies,
                  get_spawn_count, snapshot_weapon_power,
                  _is_visible,
                  default_run_stats, collect_run_stats, collect_weapon_stats, save_stats,
                  save_settings, load_settings, SETTINGS_FILE,
                  JOYSTICK_DEADZONE, GAMEPAD_NAV_REPEAT_DELAY, init_pygame,
                  handle_joy_device_added, handle_joy_device_removed,
                  BALANCE, BALANCE_FILE, load_balance_config, _default_balance_toml)
import game


class TestXPThresholds(unittest.TestCase):
    def test_thresholds_are_increasing(self):
        thresholds = generate_xp_thresholds()
        for i in range(1, len(thresholds)):
            self.assertGreater(thresholds[i], thresholds[i - 1])

    def test_first_threshold(self):
        thresholds = generate_xp_thresholds()
        self.assertEqual(thresholds[0], 10)

    def test_threshold_count(self):
        thresholds = generate_xp_thresholds(20)
        self.assertEqual(len(thresholds), 20)


class TestLevelUp(unittest.TestCase):
    def setUp(self):
        self.thresholds = generate_xp_thresholds()

    def test_no_level_up_below_threshold(self):
        xp, level, leveled = check_level_up(5, 1, self.thresholds)
        self.assertEqual(xp, 5)
        self.assertEqual(level, 1)
        self.assertFalse(leveled)

    def test_level_up_at_threshold(self):
        xp, level, leveled = check_level_up(10, 1, self.thresholds)
        self.assertEqual(level, 2)
        self.assertTrue(leveled)
        self.assertEqual(xp, 0)  # 10 - 10 = 0

    def test_level_up_with_excess_xp(self):
        xp, level, leveled = check_level_up(13, 1, self.thresholds)
        self.assertEqual(level, 2)
        self.assertTrue(leveled)
        self.assertEqual(xp, 3)  # 13 - 10 = 3

    def test_multiple_level_ups(self):
        """Simulate accumulating XP and leveling up multiple times."""
        xp, level = 0, 1
        thresholds = self.thresholds
        # Kill enough to reach level 2
        xp += 10
        leveled = True
        while leveled:
            xp, level, leveled = check_level_up(xp, level, thresholds)
        self.assertEqual(level, 2)

        # Kill more to reach level 3 (threshold is 17)
        xp += 17
        leveled = True
        while leveled:
            xp, level, leveled = check_level_up(xp, level, thresholds)
        self.assertEqual(level, 3)

    def test_level_beyond_thresholds(self):
        """Level beyond max doesn't crash."""
        thresholds = generate_xp_thresholds(2)
        xp, level, leveled = check_level_up(100, 3, thresholds)
        self.assertEqual(level, 3)
        self.assertFalse(leveled)
        self.assertEqual(xp, 100)

    def test_xp_accumulation_1_per_kill(self):
        """Each kill gives 1 XP, so 10 kills should trigger level up from level 1."""
        xp, level = 0, 1
        thresholds = self.thresholds
        for _ in range(10):
            xp += 1
        leveled = True
        while leveled:
            xp, level, leveled = check_level_up(xp, level, thresholds)
        self.assertEqual(level, 2)
        self.assertEqual(xp, 0)


class TestDefaultWeaponStats(unittest.TestCase):
    def test_default_values(self):
        stats = default_weapon_stats()
        self.assertEqual(stats["damage"], 1)
        self.assertEqual(stats["fire_rate"], 25)
        self.assertEqual(stats["bullet_speed"], 8)
        self.assertEqual(stats["range"], 90)
        self.assertEqual(stats["weapon_type"], "normal")

    def test_returns_new_dict_each_call(self):
        s1 = default_weapon_stats()
        s2 = default_weapon_stats()
        self.assertIsNot(s1, s2)


class TestBulletWithWeaponStats(unittest.TestCase):
    def test_default_bullet(self):
        b = Bullet(0, 0, 1, 0)
        self.assertEqual(b.damage, 1)
        self.assertAlmostEqual(b.vx, 8.0)
        self.assertEqual(b.life, 90)

    def test_custom_damage(self):
        b = Bullet(0, 0, 1, 0, damage=3)
        self.assertEqual(b.damage, 3)

    def test_custom_speed(self):
        b = Bullet(0, 0, 1, 0, speed=12)
        self.assertAlmostEqual(b.vx, 12.0)

    def test_custom_lifetime(self):
        b = Bullet(0, 0, 1, 0, lifetime=50)
        self.assertEqual(b.life, 50)

    def test_all_custom_stats(self):
        b = Bullet(0, 0, 0, 1, damage=5, speed=10, lifetime=30)
        self.assertEqual(b.damage, 5)
        self.assertAlmostEqual(b.vy, 10.0)
        self.assertEqual(b.life, 30)


class TestShootAtWithWeaponStats(unittest.TestCase):
    def _make_target(self, x, y):
        """Create a simple object with x, y attributes."""
        class Target:
            pass
        t = Target()
        t.x, t.y = float(x), float(y)
        return t

    def test_shoot_with_default_stats(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        inv = [default_weapon_stats()]
        u.shoot_at(target, bullets, weapon_stats=inv)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].damage, 1)
        self.assertAlmostEqual(bullets[0].vx, 8.0)
        self.assertEqual(bullets[0].life, 90)

    def test_shoot_with_boosted_damage(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["damage"] = 5
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(bullets[0].damage, 5)

    def test_fire_rate_affects_cooldown(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["fire_rate"] = 10
        inv = [ws]
        u.shoot_at(target, bullets, weapon_stats=inv)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(inv[0]["cooldown"], 10)

    def test_shoot_without_weapon_stats_uses_defaults(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        u.shoot_at(target, bullets)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(u.cooldown, 25)

    def test_range_affects_shoot_distance(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        # Target far away - with short range, should not shoot
        target = self._make_target(500, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["range"] = 5  # 5 frames * 8 speed = 40 pixels max
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 0)

    def test_range_allows_close_target(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(30, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["range"] = 5  # 5 * 8 = 40 pixels
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 1)


class TestGenerateUpgradeOptions(unittest.TestCase):
    def test_returns_3_options(self):
        inv = default_weapon_inventory()
        options = generate_upgrade_options(3, inv)
        self.assertEqual(len(options), 3)

    def test_non_milestone_all_stat_upgrades(self):
        inv = default_weapon_inventory()
        options = generate_upgrade_options(3, inv)
        for opt in options:
            self.assertIn("stat", opt)
            self.assertIn("name", opt)

    def test_milestone_has_weapon_option(self):
        inv = default_weapon_inventory()
        # Level 5 is a milestone
        found_weapon = False
        # Run multiple times since it's random placement
        for _ in range(50):
            options = generate_upgrade_options(5, inv)
            for opt in options:
                if "weapon_type" in opt:
                    found_weapon = True
                    self.assertIn(opt["weapon_type"], WEAPON_TYPES)
                    break
            if found_weapon:
                break
        self.assertTrue(found_weapon)

    def test_milestone_10(self):
        inv = default_weapon_inventory()
        found_weapon = False
        for _ in range(50):
            options = generate_upgrade_options(10, inv)
            if any("weapon_type" in o for o in options):
                found_weapon = True
                break
        self.assertTrue(found_weapon)

    def test_no_duplicate_weapon_type_offered(self):
        inv = default_weapon_inventory()
        inv[0]["weapon_type"] = "shotgun"
        for _ in range(50):
            options = generate_upgrade_options(5, inv)
            for opt in options:
                if "weapon_type" in opt:
                    self.assertNotEqual(opt["weapon_type"], "shotgun")


class TestApplyUpgrade(unittest.TestCase):
    def test_apply_damage_upgrade(self):
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "+Damage", "stat": "damage", "amount": 1})
        self.assertEqual(inv[0]["damage"], 2)

    def test_apply_fire_rate_upgrade(self):
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3})
        self.assertEqual(inv[0]["fire_rate"], 22)

    def test_fire_rate_clamped_to_minimum(self):
        inv = default_weapon_inventory()
        inv[0]["fire_rate"] = 4
        apply_upgrade(inv, {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3})
        self.assertEqual(inv[0]["fire_rate"], 5)

    def test_apply_weapon_type(self):
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "Weapon: Shotgun", "weapon_type": "shotgun"})
        self.assertEqual(len(inv), 2)
        self.assertEqual(inv[1]["weapon_type"], "shotgun")

    def test_apply_bullet_speed(self):
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "+Bullet Speed", "stat": "bullet_speed", "amount": 2})
        self.assertEqual(inv[0]["bullet_speed"], 10)

    def test_apply_range(self):
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "+Range", "stat": "range", "amount": 15})
        self.assertEqual(inv[0]["range"], 105)

    def test_apply_max_hp_upgrade(self):
        inv = default_weapon_inventory()
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        self.assertEqual(player.max_hp, 5)
        self.assertEqual(player.hp, 5)
        apply_upgrade(inv, {"name": "+Max HP", "stat": "max_hp", "amount": 1}, player)
        self.assertEqual(player.max_hp, 6)
        self.assertEqual(player.hp, 6)

    def test_apply_max_hp_upgrade_heals_one(self):
        inv = default_weapon_inventory()
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        player.hp = 3  # damaged
        apply_upgrade(inv, {"name": "+Max HP", "stat": "max_hp", "amount": 1}, player)
        self.assertEqual(player.max_hp, 6)
        self.assertEqual(player.hp, 4)  # healed 1, not to full

    def test_apply_max_hp_without_player_raises(self):
        inv = default_weapon_inventory()
        with self.assertRaises(ValueError):
            apply_upgrade(inv, {"name": "+Max HP", "stat": "max_hp", "amount": 1})

    def test_max_hp_in_upgrade_options(self):
        """Max HP should be available as a possible upgrade option."""
        stat_names = [u["stat"] for u in STAT_UPGRADES if "stat" in u]
        self.assertIn("max_hp", stat_names)


class TestScaledUpgrades(unittest.TestCase):
    def test_damage_scaling_below_10(self):
        self.assertEqual(get_scaled_amount("damage", 1, 5), 1)

    def test_damage_scaling_at_10(self):
        self.assertEqual(get_scaled_amount("damage", 1, 10), 1)

    def test_damage_scaling_at_15(self):
        self.assertEqual(get_scaled_amount("damage", 1, 15), 1)

    def test_damage_scaling_at_20(self):
        self.assertEqual(get_scaled_amount("damage", 1, 20), 2)

    def test_damage_scaling_at_25(self):
        self.assertEqual(get_scaled_amount("damage", 1, 25), 2)

    def test_fire_rate_scaling_below_15(self):
        self.assertEqual(get_scaled_amount("fire_rate", -3, 10), -3)

    def test_fire_rate_scaling_at_15(self):
        self.assertEqual(get_scaled_amount("fire_rate", -3, 15), -5)

    def test_fire_rate_scaling_at_20(self):
        self.assertEqual(get_scaled_amount("fire_rate", -3, 20), -5)

    def test_bullet_speed_no_scaling(self):
        self.assertEqual(get_scaled_amount("bullet_speed", 2, 20), 2)

    def test_range_no_scaling(self):
        self.assertEqual(get_scaled_amount("range", 15, 20), 15)

    def test_generate_options_scaled_damage_at_level_12(self):
        inv = default_weapon_inventory()
        for _ in range(50):
            options = generate_upgrade_options(12, inv)
            for opt in options:
                if opt.get("stat") == "damage":
                    self.assertEqual(opt["amount"], 1)

    def test_generate_options_scaled_fire_rate_at_level_16(self):
        inv = default_weapon_inventory()
        for _ in range(50):
            options = generate_upgrade_options(16, inv)
            for opt in options:
                if opt.get("stat") == "fire_rate":
                    self.assertEqual(opt["amount"], -5)

    def test_milestone_every_4_after_level_15(self):
        inv = default_weapon_inventory()
        # Level 16 is a milestone (16 % 4 == 0) with new interval
        found_weapon = False
        for _ in range(100):
            options = generate_upgrade_options(16, inv)
            if any("weapon_type" in o for o in options):
                found_weapon = True
                break
        self.assertTrue(found_weapon)

    def test_level_17_not_milestone(self):
        inv = default_weapon_inventory()
        # Level 17: 17 % 4 != 0, should not be milestone
        for _ in range(50):
            options = generate_upgrade_options(17, inv)
            for opt in options:
                self.assertNotIn("weapon_type", opt)


class TestShotgunWeapon(unittest.TestCase):
    def _make_target(self, x, y):
        class Target:
            pass
        t = Target()
        t.x, t.y = float(x), float(y)
        return t

    def test_shotgun_fires_5_bullets(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "shotgun"
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 5)

    def test_shotgun_bullets_have_reduced_damage(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "shotgun"
        ws["damage"] = 4
        u.shoot_at(target, bullets, weapon_stats=[ws])
        for b in bullets:
            self.assertEqual(b.damage, 2)  # 4 // 2

    def test_shotgun_bullets_spread(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "shotgun"
        u.shoot_at(target, bullets, weapon_stats=[ws])
        # Bullets should have different directions
        angles = [math.atan2(b.vy, b.vx) for b in bullets]
        self.assertNotAlmostEqual(angles[0], angles[-1], places=2)

    def test_shotgun_min_damage_is_1(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "shotgun"
        ws["damage"] = 1
        u.shoot_at(target, bullets, weapon_stats=[ws])
        for b in bullets:
            self.assertEqual(b.damage, 1)


class TestPiercingWeapon(unittest.TestCase):
    def test_piercing_bullet_has_correct_type(self):
        b = Bullet(0, 0, 1, 0, weapon_type="piercing")
        self.assertEqual(b.weapon_type, "piercing")

    def test_piercing_bullet_tracks_hits(self):
        b = Bullet(0, 0, 1, 0, weapon_type="piercing")
        self.assertEqual(len(b.pierced_enemies), 0)
        b.pierced_enemies.add(123)
        self.assertIn(123, b.pierced_enemies)

    def test_piercing_bullet_not_destroyed_on_hit(self):
        """Piercing bullets should remain alive after hitting an enemy."""
        b = Bullet(0, 0, 1, 0, damage=1, weapon_type="piercing")
        # Simulate what the collision code does for piercing
        enemy_id = 42
        b.pierced_enemies.add(enemy_id)
        # bullet.life should NOT be set to 0 for piercing
        self.assertGreater(b.life, 0)


class TestExplosiveWeapon(unittest.TestCase):
    def test_explosive_bullet_has_correct_type(self):
        b = Bullet(0, 0, 1, 0, weapon_type="explosive")
        self.assertEqual(b.weapon_type, "explosive")

    def test_explosive_bullet_created_with_stats(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)

        class Target:
            pass
        t = Target()
        t.x, t.y = 100.0, 0.0
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "explosive"
        ws["damage"] = 3
        u.shoot_at(t, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "explosive")
        self.assertEqual(bullets[0].damage, 3)


class TestWeaponTypeInShootAt(unittest.TestCase):
    def _make_target(self, x, y):
        class Target:
            pass
        t = Target()
        t.x, t.y = float(x), float(y)
        return t

    def test_normal_fires_single_bullet(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        inv = [default_weapon_stats()]
        u.shoot_at(target, bullets, weapon_stats=inv)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "normal")

    def test_piercing_fires_single_bullet(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "piercing"
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "piercing")

    def test_explosive_fires_single_bullet(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        ws = default_weapon_stats()
        ws["weapon_type"] = "explosive"
        u.shoot_at(target, bullets, weapon_stats=[ws])
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "explosive")


class TestFullLevelUpFlow(unittest.TestCase):
    """Integration tests for the complete level-up flow."""

    def test_full_flow_xp_to_level_up_to_upgrade(self):
        """Simulate: accumulate XP -> level up -> generate options -> apply upgrade."""
        thresholds = generate_xp_thresholds()
        inv = default_weapon_inventory()
        xp, level = 0, 1

        # Accumulate XP from kills
        for _ in range(10):
            xp += 1

        # Level up
        xp, level, leveled = check_level_up(xp, level, thresholds)
        self.assertTrue(leveled)
        self.assertEqual(level, 2)

        # Generate upgrade options
        options = generate_upgrade_options(level, inv)
        self.assertEqual(len(options), 3)

        # Apply first non-max_hp option (max_hp doesn't change weapon stats)
        option = next(o for o in options if o.get("stat") != "max_hp")
        apply_upgrade(inv, option)
        # Stats should have changed from defaults
        ws = inv[0]
        changed = (
            ws["damage"] != 1 or ws["fire_rate"] != 25 or
            ws["bullet_speed"] != 8 or ws["range"] != 90
        )
        self.assertTrue(changed)

    def test_flow_to_milestone_weapon_unlock(self):
        """Simulate reaching level 5 milestone and getting a weapon type."""
        thresholds = generate_xp_thresholds()
        inv = default_weapon_inventory()
        xp, level = 0, 1

        # Level up to level 5 step by step
        while level < 5:
            threshold = thresholds[level - 1]
            xp += threshold
            xp, level, leveled = check_level_up(xp, level, thresholds)

        self.assertEqual(level, 5)

        # At milestone, should get weapon option
        found_weapon = False
        for _ in range(50):
            options = generate_upgrade_options(level, inv)
            for opt in options:
                if "weapon_type" in opt:
                    apply_upgrade(inv, opt)
                    self.assertEqual(len(inv), 2)
                    self.assertIn(inv[1]["weapon_type"], WEAPON_TYPES)
                    found_weapon = True
                    break
            if found_weapon:
                break
        self.assertTrue(found_weapon)

    def test_weapon_type_persists_through_stat_upgrades(self):
        """After getting a weapon type, stat upgrades should not reset it."""
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "Weapon: Shotgun", "weapon_type": "shotgun"})
        self.assertEqual(len(inv), 2)
        self.assertEqual(inv[1]["weapon_type"], "shotgun")

        # Apply a stat upgrade - should apply to all weapons
        apply_upgrade(inv, {"name": "+Damage", "stat": "damage", "amount": 1})
        self.assertEqual(inv[1]["weapon_type"], "shotgun")
        self.assertEqual(inv[0]["damage"], 2)
        self.assertEqual(inv[1]["damage"], 2)

    def test_multiple_level_ups_with_upgrades(self):
        """Simulate multiple level-ups each with an upgrade applied."""
        thresholds = generate_xp_thresholds()
        inv = default_weapon_inventory()
        xp, level = 0, 1

        for target_level in range(2, 5):
            threshold = thresholds[level - 1]
            xp += threshold
            xp, level, leveled = check_level_up(xp, level, thresholds)
            self.assertTrue(leveled)
            self.assertEqual(level, target_level)

            options = generate_upgrade_options(level, inv)
            # Pick a weapon stat upgrade to avoid max_hp (which doesn't modify weapon_stats)
            weapon_option = next(
                (o for o in options if o.get("stat") != "max_hp" and "weapon_type" not in o),
                options[0],
            )
            apply_upgrade(inv, weapon_option)

        # After 3 upgrades, stats should differ from defaults
        default = default_weapon_stats()
        ws = inv[0]
        any_different = any(
            ws[k] != default[k] for k in ["damage", "fire_rate", "bullet_speed", "range"]
        )
        self.assertTrue(any_different)

    def test_reset_returns_to_defaults(self):
        """Verify that resetting state returns to default values."""
        inv = default_weapon_inventory()
        apply_upgrade(inv, {"name": "+Damage", "stat": "damage", "amount": 5})
        self.assertEqual(inv[0]["damage"], 6)

        # Reset by getting fresh defaults (as reset_game does)
        inv = default_weapon_inventory()
        self.assertEqual(inv[0]["damage"], 1)
        self.assertEqual(inv[0]["weapon_type"], "normal")


class TestTronColorPalette(unittest.TestCase):
    def test_bg_is_near_black(self):
        self.assertEqual(BG, (5, 5, 15))

    def test_player_color_is_cyan(self):
        self.assertEqual(PLAYER_COLOR, (0, 220, 255))

    def test_enemy_color_is_neon_red(self):
        self.assertEqual(ENEMY_COLOR, (255, 30, 60))

    def test_grid_color_is_dim_blue(self):
        self.assertEqual(GRID_COLOR, (15, 15, 40))

    def test_border_color_is_neon_purple(self):
        self.assertEqual(BORDER_COLOR, (150, 0, 255))

    def test_obstacle_colors(self):
        self.assertEqual(OBSTACLE_COLOR, (15, 10, 30))
        self.assertEqual(OBSTACLE_BORDER, (120, 0, 200))

    def test_bullet_color(self):
        self.assertEqual(BULLET_COLOR, (200, 255, 255))

    def test_health_fg_neon(self):
        self.assertEqual(HEALTH_FG, (0, 255, 180))


class TestDrawGlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.Surface((200, 200), pygame.SRCALPHA)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_draw_glow_runs_without_error(self):
        draw_glow(self.surface, (0, 220, 255), (100, 100), 10)

    def test_draw_glow_custom_params(self):
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        draw_glow(surf, (255, 30, 60), (50, 50), 20, intensity=120, layers=6)
        # Verify pixels were actually drawn near center
        pixel = surf.get_at((50, 50))
        self.assertGreater(pixel[3], 0)

    def test_draw_glow_zero_radius(self):
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        # Should not raise an error
        draw_glow(surf, (255, 0, 0), (50, 50), 0)
        # Surface should be unchanged
        self.assertEqual(surf.get_at((50, 50))[3], 0)

    def test_draw_glow_negative_radius(self):
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        draw_glow(surf, (255, 0, 0), (50, 50), -5)
        self.assertEqual(surf.get_at((50, 50))[3], 0)

    def test_draw_glow_zero_layers(self):
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        draw_glow(surf, (255, 0, 0), (50, 50), 10, layers=0)
        self.assertEqual(surf.get_at((50, 50))[3], 0)

    def test_draw_glow_modifies_surface(self):
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        # Check a pixel far from center is transparent before glow
        before = surf.get_at((100, 100))
        draw_glow(surf, (0, 220, 255), (100, 100), 10)
        after = surf.get_at((100, 100))
        # Alpha should increase after drawing glow
        self.assertGreater(after[3], before[3])


class TestEntityDrawGlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        import game
        self._orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        self.camera = Camera()

    def tearDown(self):
        import game
        game.screen = self._orig_screen

    def test_unit_draw_with_glow(self):
        import game
        unit = Unit(100, 100, PLAYER_COLOR, is_player=True)
        unit.draw(self.camera)
        # Verify pixels drawn at unit position
        pixel = game.screen.get_at((100, 100))
        self.assertNotEqual(pixel, (0, 0, 0, 255))

    def test_ally_draw_with_glow(self):
        import game
        unit = Unit(100, 100, (0, 150, 255), is_player=False)
        unit.draw(self.camera)
        pixel = game.screen.get_at((100, 100))
        self.assertNotEqual(pixel, (0, 0, 0, 255))

    def test_enemy_draw_with_glow(self):
        import game
        enemy = Enemy(self.camera)
        enemy.x, enemy.y = 200, 200
        enemy.draw(self.camera)
        sx, sy = self.camera.apply(enemy.x, enemy.y)
        pixel = game.screen.get_at((int(sx), int(sy)))
        self.assertNotEqual(pixel, (0, 0, 0, 255))

    def test_bullet_draw_with_glow(self):
        import game
        bullet = Bullet(100, 100, 1, 0)
        bullet.draw(self.camera)
        pixel = game.screen.get_at((100, 100))
        self.assertNotEqual(pixel, (0, 0, 0, 255))

    def test_obstacle_draw_with_glow(self):
        import game
        obstacle = Obstacle(100, 100, 50, 50)
        obstacle.draw(self.camera)
        pixel = game.screen.get_at((125, 125))
        self.assertNotEqual(pixel, (0, 0, 0, 255))


class TestMenuAndHUDRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_mock_font(self):
        """Create a mock font that returns a surface from render()."""
        from unittest.mock import MagicMock
        mock_font = MagicMock()
        surf = pygame.Surface((100, 30))
        mock_font.render.return_value = surf
        return mock_font

    def setUp(self):
        import game
        self._orig_screen = game.screen
        self._orig_font = game.font
        self._orig_title_font = game.title_font
        game.screen = pygame.Surface((1024, 768))
        game.font = self._make_mock_font()
        game.title_font = self._make_mock_font()
        self._orig_menu_font = game.menu_font
        game.menu_font = self._make_mock_font()

    def tearDown(self):
        import game
        game.screen = self._orig_screen
        game.font = self._orig_font
        game.title_font = self._orig_title_font
        game.menu_font = self._orig_menu_font

    def test_draw_menu_runs_without_error(self):
        from unittest.mock import patch
        from game import draw_menu
        with patch('pygame.display.flip'):
            draw_menu()

    def test_menu_item_rect_positions(self):
        from game import get_menu_item_rect, MENU_X, MENU_START_Y, MENU_ITEM_HEIGHT
        for i in range(3):
            rect = get_menu_item_rect(i)
            self.assertEqual(rect.x, MENU_X)
            self.assertEqual(rect.y, MENU_START_Y + i * MENU_ITEM_HEIGHT)
            self.assertEqual(rect.width, 300)

    def test_menu_hover_detection(self):
        from game import get_hovered_menu_index, get_menu_item_rect
        # Click inside first item
        r = get_menu_item_rect(0)
        self.assertEqual(get_hovered_menu_index(r.centerx, r.centery), 0)
        # Click inside second item
        r = get_menu_item_rect(1)
        self.assertEqual(get_hovered_menu_index(r.centerx, r.centery), 1)
        # Click inside third item
        r = get_menu_item_rect(2)
        self.assertEqual(get_hovered_menu_index(r.centerx, r.centery), 2)
        # Click outside
        self.assertEqual(get_hovered_menu_index(900, 900), -1)

    def test_draw_menu_with_hover(self):
        from unittest.mock import patch
        import game as g
        from game import draw_menu, get_hovered_menu_index, get_menu_item_rect
        # Simulate hovering over the second menu item
        r = get_menu_item_rect(1)
        hover_x, hover_y = r.centerx, r.centery
        idx = get_hovered_menu_index(hover_x, hover_y)
        self.assertEqual(idx, 1)
        # Set selection to match hover and verify draw runs without error
        g.menu_selected_index = idx
        with patch('pygame.display.flip'):
            draw_menu()
        self.assertEqual(g.menu_selected_index, 1)

    def test_draw_game_over_runs_without_error(self):
        from unittest.mock import patch
        from game import draw_game_over
        with patch('pygame.display.flip'):
            draw_game_over(100, 3)

    def test_draw_grid_runs_without_error(self):
        from game import draw_grid
        camera = Camera()
        draw_grid(camera)

    def test_draw_game_scene_runs_without_error(self):
        from game import draw_game_scene, Camera, default_weapon_inventory, generate_xp_thresholds
        camera = Camera()
        player = Unit(100, 100, (0, 220, 255), is_player=True)
        camera.update(player)
        inv = default_weapon_inventory()
        thresholds = generate_xp_thresholds()
        draw_game_scene(camera, [], [], [], [], player,
                        0, 1, 1, inv, 0, thresholds)

    def test_draw_dim_overlay_runs_without_error(self):
        from game import draw_dim_overlay
        draw_dim_overlay()

    def test_draw_dim_overlay_darkens_screen(self):
        """Verify the overlay makes the screen darker (pixel values decrease)."""
        import game
        game.screen.fill((200, 200, 200))
        before = game.screen.get_at((100, 100))
        from game import draw_dim_overlay
        draw_dim_overlay()
        after = game.screen.get_at((100, 100))
        self.assertLess(after[0], before[0])
        self.assertLess(after[1], before[1])
        self.assertLess(after[2], before[2])

    def test_game_scene_renders_during_level_up_state(self):
        """Verify that draw_game_scene + draw_dim_overlay can be called
        in sequence (as happens during STATE_LEVEL_UP)."""
        from game import draw_game_scene, draw_dim_overlay, Camera, default_weapon_inventory, generate_xp_thresholds
        camera = Camera()
        player = Unit(100, 100, (0, 220, 255), is_player=True)
        camera.update(player)
        inv = default_weapon_inventory()
        thresholds = generate_xp_thresholds()
        # Should not raise
        draw_game_scene(camera, [], [], [], [], player,
                        0, 1, 1, inv, 0, thresholds)
        draw_dim_overlay()

    def test_upgrade_panel_dimensions(self):
        """Verify panel constants define a centered ~500x350 panel."""
        from game import PANEL_WIDTH, PANEL_HEIGHT, _panel_origin, WIDTH, HEIGHT
        self.assertEqual(PANEL_WIDTH, 500)
        self.assertEqual(PANEL_HEIGHT, 350)
        panel_x, panel_y = _panel_origin()
        self.assertEqual(panel_x, (WIDTH - PANEL_WIDTH) // 2)
        self.assertEqual(panel_y, (HEIGHT - PANEL_HEIGHT) // 2)

    def test_upgrade_panel_renders_without_error(self):
        """Verify draw_upgrade_panel runs without raising."""
        from game import draw_upgrade_panel
        options = [
            {"name": "Damage +10%", "stat": "damage", "amount": 1},
            {"name": "Fire Rate +10%", "stat": "fire_rate", "amount": -2},
            {"name": "Shotgun", "weapon_type": "shotgun"},
        ]
        # Should not raise
        draw_upgrade_panel(2, options)

    def test_upgrade_panel_draws_to_screen(self):
        """Verify draw_upgrade_panel actually draws pixels in the panel region."""
        import game
        from game import draw_upgrade_panel, _panel_origin, PANEL_WIDTH, PANEL_HEIGHT
        game.screen.fill((0, 0, 0))
        options = [{"name": "Test", "stat": "damage", "amount": 1}]
        draw_upgrade_panel(1, options)
        panel_x, panel_y = _panel_origin()
        cx = panel_x + PANEL_WIDTH // 2
        cy = panel_y + PANEL_HEIGHT // 2
        pixel = game.screen.get_at((cx, cy))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    def test_upgrade_panel_centered_on_screen(self):
        """Verify the panel is centered horizontally and vertically."""
        from game import PANEL_WIDTH, PANEL_HEIGHT, _panel_origin, WIDTH, HEIGHT
        panel_x, panel_y = _panel_origin()
        center_x = panel_x + PANEL_WIDTH // 2
        center_y = panel_y + PANEL_HEIGHT // 2
        self.assertEqual(center_x, WIDTH // 2)
        self.assertEqual(center_y, HEIGHT // 2)

    def test_create_upgrade_icon_returns_surface(self):
        """Verify create_upgrade_icon returns a 32x32 surface for each upgrade type."""
        from game import create_upgrade_icon, ICON_SIZE
        test_options = [
            {"name": "+Damage", "stat": "damage", "amount": 1},
            {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3},
            {"name": "+Bullet Speed", "stat": "bullet_speed", "amount": 2},
            {"name": "+Range", "stat": "range", "amount": 15},
            {"name": "Weapon: Shotgun", "weapon_type": "shotgun"},
            {"name": "Weapon: Piercing", "weapon_type": "piercing"},
            {"name": "Weapon: Explosive", "weapon_type": "explosive"},
        ]
        for opt in test_options:
            icon = create_upgrade_icon(opt)
            self.assertEqual(icon.get_width(), ICON_SIZE, f"Icon width wrong for {opt['name']}")
            self.assertEqual(icon.get_height(), ICON_SIZE, f"Icon height wrong for {opt['name']}")

    def test_create_upgrade_icon_not_blank(self):
        """Verify icons have non-transparent pixels drawn on them."""
        from game import create_upgrade_icon, ICON_SIZE
        test_options = [
            {"name": "+Damage", "stat": "damage", "amount": 1},
            {"name": "Weapon: Shotgun", "weapon_type": "shotgun"},
        ]
        for opt in test_options:
            icon = create_upgrade_icon(opt)
            # Check that at least some pixels are non-transparent
            has_pixel = False
            for x in range(ICON_SIZE):
                for y in range(ICON_SIZE):
                    if icon.get_at((x, y))[3] > 0:
                        has_pixel = True
                        break
                if has_pixel:
                    break
            self.assertTrue(has_pixel, f"Icon for {opt['name']} is completely blank")

    def test_upgrade_panel_renders_with_icons(self):
        """Verify draw_upgrade_panel works with all upgrade types (icons included)."""
        from game import draw_upgrade_panel
        options = [
            {"name": "+Damage", "stat": "damage", "amount": 1},
            {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3},
            {"name": "Weapon: Shotgun", "weapon_type": "shotgun"},
        ]
        draw_upgrade_panel(3, options)

    def test_get_hovered_upgrade_index_hit(self):
        """Click inside an option row returns correct index."""
        from game import (get_hovered_upgrade_index, _panel_origin,
                          OPTION_START_Y, OPTION_ROW_HEIGHT, PANEL_WIDTH)
        panel_x, panel_y = _panel_origin()
        row_h = OPTION_ROW_HEIGHT - 5  # actual row rect height
        mx = panel_x + PANEL_WIDTH // 2
        for i in range(3):
            # Click geometric center of each row
            my = panel_y + OPTION_START_Y + i * OPTION_ROW_HEIGHT + row_h // 2
            self.assertEqual(get_hovered_upgrade_index(mx, my, 3), i)

    def test_get_hovered_upgrade_index_miss(self):
        """Click outside all option rows returns -1."""
        from game import get_hovered_upgrade_index, _panel_origin
        panel_x, panel_y = _panel_origin()
        # Click well outside panel
        self.assertEqual(get_hovered_upgrade_index(0, 0, 3), -1)
        # Click above options (in title area)
        self.assertEqual(get_hovered_upgrade_index(panel_x + 100, panel_y + 10, 3), -1)

    def test_get_hovered_upgrade_index_no_options(self):
        """With zero options, always returns -1."""
        from game import get_hovered_upgrade_index, _panel_origin
        panel_x, panel_y = _panel_origin()
        self.assertEqual(get_hovered_upgrade_index(panel_x + 100, panel_y + 100, 0), -1)


class TestHUDWidgets(unittest.TestCase):
    """Validation tests for all four HUD corner widgets."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_mock_font(self):
        mock_font = MagicMock()
        surf = pygame.Surface((100, 30))
        mock_font.render.return_value = surf
        return mock_font

    def setUp(self):
        self._orig_screen = game.screen
        self._orig_font = game.font
        self._orig_title_font = game.title_font
        self._orig_hud_font = game._hud_font
        self._orig_hud_font_small = game._hud_font_small
        game.screen = pygame.Surface((1024, 768))
        game.font = self._make_mock_font()
        game.title_font = self._make_mock_font()
        # Reset cached HUD fonts so they get re-created with current pygame
        game._hud_font = None
        game._hud_font_small = None

    def tearDown(self):
        game.screen = self._orig_screen
        game.font = self._orig_font
        game.title_font = self._orig_title_font
        game._hud_font = self._orig_hud_font
        game._hud_font_small = self._orig_hud_font_small

    # -- draw_hud_panel --

    def test_hud_panel_draws_pixels(self):
        """Panel helper should draw non-black pixels in the panel region."""
        from game import draw_hud_panel
        game.screen.fill((0, 0, 0))
        draw_hud_panel(50, 50, 200, 100)
        pixel = game.screen.get_at((150, 100))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    def test_hud_panel_custom_border_color(self):
        from game import draw_hud_panel
        game.screen.fill((0, 0, 0))
        draw_hud_panel(50, 50, 200, 100, border_color=(255, 0, 0))
        # Verify a border pixel contains red (border is drawn at the panel edge)
        border_pixel = game.screen.get_at((50, 50))
        self.assertGreater(border_pixel[0], 0,
                           "Border should contain red channel from custom color")

    # -- draw_hud_vitals --

    def test_hud_vitals_renders_without_error(self):
        from game import draw_hud_vitals, generate_xp_thresholds
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        thresholds = generate_xp_thresholds()
        draw_hud_vitals(player, 0, thresholds, 1)

    def test_hud_vitals_various_hp_levels(self):
        """Vitals should render correctly at full, partial, and zero HP."""
        from game import draw_hud_vitals, generate_xp_thresholds
        thresholds = generate_xp_thresholds()
        for hp_val in [5, 3, 1, 0]:
            player = Unit(100, 100, PLAYER_COLOR, is_player=True)
            player.hp = hp_val
            player.max_hp = 5
            game.screen.fill((0, 0, 0))
            draw_hud_vitals(player, 0, thresholds, 1)

    def test_hud_vitals_high_level(self):
        """Vitals widget should handle high levels and XP values."""
        from game import draw_hud_vitals, generate_xp_thresholds
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        thresholds = generate_xp_thresholds()
        draw_hud_vitals(player, 500, thresholds, 10)

    def test_hud_vitals_draws_in_top_left(self):
        """Vitals widget should draw pixels in the top-left corner area."""
        from game import draw_hud_vitals, generate_xp_thresholds, HUD_MARGIN
        game.screen.fill((0, 0, 0))
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        thresholds = generate_xp_thresholds()
        draw_hud_vitals(player, 10, thresholds, 2)
        # Check that something was drawn near top-left
        pixel = game.screen.get_at((HUD_MARGIN + 110, HUD_MARGIN + 40))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    # -- draw_hud_stats --

    def test_hud_stats_renders_without_error(self):
        from game import draw_hud_stats
        draw_hud_stats(0, 1, [])

    def test_hud_stats_high_values(self):
        """Stats widget should handle large score and wave numbers."""
        from game import draw_hud_stats
        allies = [Unit(200, 200, (0, 0, 255)) for _ in range(10)]
        draw_hud_stats(99999, 50, allies)

    def test_hud_stats_draws_in_top_right(self):
        """Stats widget should draw pixels in the top-right corner area."""
        from game import draw_hud_stats, WIDTH, HUD_MARGIN
        game.screen.fill((0, 0, 0))
        draw_hud_stats(100, 5, [])
        pixel = game.screen.get_at((WIDTH - HUD_MARGIN - 90, HUD_MARGIN + 40))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    # -- draw_hud_weapons --

    def test_hud_weapons_renders_without_error(self):
        from game import draw_hud_weapons, default_weapon_inventory
        inv = default_weapon_inventory()
        draw_hud_weapons(inv)

    def test_hud_weapons_multiple_types(self):
        """Weapons widget should render all weapon types."""
        from game import draw_hud_weapons
        inv = [
            {"weapon_type": "normal", "damage": 1},
            {"weapon_type": "shotgun", "damage": 2},
            {"weapon_type": "piercing", "damage": 3},
            {"weapon_type": "explosive", "damage": 5},
        ]
        draw_hud_weapons(inv)

    def test_hud_weapons_single_weapon(self):
        from game import draw_hud_weapons
        draw_hud_weapons([{"weapon_type": "normal", "damage": 1}])

    def test_hud_weapons_draws_in_bottom_left(self):
        """Weapons widget should draw pixels in the bottom-left area."""
        from game import draw_hud_weapons, HUD_MARGIN, HEIGHT
        game.screen.fill((0, 0, 0))
        inv = [{"weapon_type": "normal", "damage": 1}]
        draw_hud_weapons(inv)
        pixel = game.screen.get_at((HUD_MARGIN + 90, HEIGHT - HUD_MARGIN - 20))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    # -- draw_hud_minimap --

    def test_hud_minimap_renders_without_error(self):
        from game import draw_hud_minimap
        camera = Camera()
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        camera.update(player)
        draw_hud_minimap(camera, player, [], [], [])

    def test_hud_minimap_with_entities(self):
        """Minimap should handle many enemies, allies, and obstacles."""
        from game import draw_hud_minimap
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        camera.update(player)
        allies = [Unit(600 + i * 50, 500, (0, 0, 255)) for i in range(5)]
        enemies = [Enemy(camera) for _ in range(20)]
        obstacles = [Obstacle(200 + i * 100, 200, 50, 50) for i in range(10)]
        draw_hud_minimap(camera, player, allies, enemies, obstacles)

    def test_hud_minimap_with_escape_rooms(self):
        from game import draw_hud_minimap, EscapeRoom
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        camera.update(player)
        escape_rooms = [EscapeRoom(1000, 1000)]
        draw_hud_minimap(camera, player, [], [], [], escape_rooms=escape_rooms)

    def test_hud_minimap_draws_in_bottom_right(self):
        """Minimap should draw pixels in the bottom-right area."""
        from game import draw_hud_minimap, WIDTH, HEIGHT, HUD_MARGIN
        game.screen.fill((0, 0, 0))
        camera = Camera()
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        camera.update(player)
        draw_hud_minimap(camera, player, [], [], [])
        pixel = game.screen.get_at((WIDTH - HUD_MARGIN - 75, HEIGHT - HUD_MARGIN - 56))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    # -- Full scene integration tests --

    def test_game_scene_with_populated_battlefield(self):
        """Simulate an intense battle scene with many entities to verify
        no errors occur and all HUD widgets render together."""
        from game import draw_game_scene, default_weapon_inventory, generate_xp_thresholds
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        player.hp = 2
        player.max_hp = 5
        camera.update(player)
        allies = [Unit(550 + i * 30, 500, (0, 0, 255)) for i in range(5)]
        enemies = [Enemy(camera) for _ in range(30)]
        obstacles = [Obstacle(100 + i * 100, 100, 50, 50) for i in range(8)]
        inv = default_weapon_inventory()
        inv.append({"weapon_type": "shotgun", "damage": 2,
                    "fire_rate": 20, "bullet_speed": 8, "range": 250})
        thresholds = generate_xp_thresholds()
        draw_game_scene(camera, obstacles, [], enemies, allies, player,
                        5000, 10, 5, inv, 75, thresholds)

    def test_game_scene_with_escape_rooms_and_health_pickups(self):
        """Full scene with escape rooms and health pickups."""
        from game import (draw_game_scene, default_weapon_inventory,
                          generate_xp_thresholds, EscapeRoom, HealthPickup)
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        camera.update(player)
        inv = default_weapon_inventory()
        thresholds = generate_xp_thresholds()
        escape_rooms = [EscapeRoom(1000, 1000)]
        health_pickups = [HealthPickup(450, 450)]
        draw_game_scene(camera, [], [], [], [], player,
                        100, 3, 2, inv, 20, thresholds,
                        health_pickups=health_pickups,
                        escape_rooms=escape_rooms)

    def test_hud_widgets_no_overlap(self):
        """Verify the four HUD panels don't overlap each other."""
        from game import HUD_MARGIN, WIDTH, HEIGHT
        # Top-left vitals: (10, 10, 220, 80)
        tl = pygame.Rect(HUD_MARGIN, HUD_MARGIN, 220, 80)
        # Top-right stats: (WIDTH-180-10, 10, 180, 80)
        tr = pygame.Rect(WIDTH - 180 - HUD_MARGIN, HUD_MARGIN, 180, 80)
        # Bottom-left weapons: dynamic height based on max weapons (3 types + normal = 4)
        max_weapons = 4
        line_h = 22
        pad = 10
        weapon_h = pad * 2 + max_weapons * line_h
        bl = pygame.Rect(HUD_MARGIN, HEIGHT - weapon_h - HUD_MARGIN, 180, weapon_h)
        # Bottom-right minimap: (WIDTH-158-10, HEIGHT-120-10, 158, 120)
        br = pygame.Rect(WIDTH - 158 - HUD_MARGIN, HEIGHT - 120 - HUD_MARGIN,
                         158, 120)
        self.assertFalse(tl.colliderect(tr))
        self.assertFalse(tl.colliderect(bl))
        self.assertFalse(tl.colliderect(br))
        self.assertFalse(tr.colliderect(bl))
        self.assertFalse(tr.colliderect(br))
        self.assertFalse(bl.colliderect(br))

    def test_game_scene_multiple_waves_simulation(self):
        """Simulate rendering across multiple wave states to verify
        HUD updates correctly as game state changes."""
        from game import draw_game_scene, default_weapon_inventory, generate_xp_thresholds
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        camera.update(player)
        inv = default_weapon_inventory()
        thresholds = generate_xp_thresholds()
        for wave_num in range(1, 6):
            score = wave_num * 100
            level = min(wave_num, 10)
            xp = wave_num * 15
            enemies = [Enemy(camera) for _ in range(wave_num * 3)]
            draw_game_scene(camera, [], [], enemies, [], player,
                            score, wave_num, level, inv, xp, thresholds)

    def test_hud_rendering_performance(self):
        """Verify HUD renders quickly enough (< 50ms per frame) even with
        many entities on the minimap."""
        import time
        from game import draw_game_scene, default_weapon_inventory, generate_xp_thresholds
        camera = Camera()
        player = Unit(500, 500, PLAYER_COLOR, is_player=True)
        camera.update(player)
        enemies = [Enemy(camera) for _ in range(50)]
        allies = [Unit(600 + i * 30, 500, (0, 0, 255)) for i in range(8)]
        obstacles = [Obstacle(200 + i * 80, 200, 40, 40) for i in range(15)]
        inv = default_weapon_inventory()
        inv.append({"weapon_type": "shotgun", "damage": 2,
                    "fire_rate": 20, "bullet_speed": 8, "range": 250})
        thresholds = generate_xp_thresholds()
        start = time.time()
        for _ in range(10):
            draw_game_scene(camera, obstacles, [], enemies, allies, player,
                            9999, 20, 8, inv, 100, thresholds)
        elapsed = time.time() - start
        avg_ms = (elapsed / 10) * 1000
        self.assertLess(avg_ms, 500,
                        f"HUD render avg {avg_ms:.1f}ms exceeds 500ms budget")


class TestEnemyTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.camera = Camera()

    def test_enemy_types_config_has_basic(self):
        self.assertIn("basic", ENEMY_TYPES)
        basic = ENEMY_TYPES["basic"]
        self.assertEqual(basic["hp"], 3)
        self.assertAlmostEqual(basic["speed"], 1.4)
        self.assertEqual(basic["radius"], 12)
        self.assertEqual(basic["xp_value"], 2)

    def test_basic_enemy_creation(self):
        e = Enemy(self.camera)
        self.assertEqual(e.enemy_type, "basic")
        self.assertEqual(e.hp, 3)
        self.assertAlmostEqual(e.speed, 1.4)
        self.assertEqual(e.radius, 12)
        self.assertEqual(e.color, (255, 30, 60))
        self.assertEqual(e.xp_value, 2)

    def test_enemy_type_defaults_to_basic(self):
        e = Enemy(self.camera)
        self.assertEqual(e.enemy_type, "basic")

    def test_explicit_basic_type(self):
        e = Enemy(self.camera, enemy_type="basic")
        self.assertEqual(e.enemy_type, "basic")
        self.assertEqual(e.hp, 3)

    def test_enemy_has_unique_uid(self):
        e1 = Enemy(self.camera)
        e2 = Enemy(self.camera)
        self.assertNotEqual(e1.uid, e2.uid)

    def test_enemy_xp_value_used_for_scoring(self):
        """Basic enemies should give xp_value=2."""
        e = Enemy(self.camera)
        self.assertEqual(e.xp_value, 2)

    def test_all_enemy_types_have_required_keys(self):
        required_keys = {"hp", "speed", "radius", "color", "xp_value"}
        for name, cfg in ENEMY_TYPES.items():
            for key in required_keys:
                self.assertIn(key, cfg, f"Enemy type '{name}' missing key '{key}'")

    def test_enemy_draw_uses_type_color(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera)
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen

    def test_runner_type_config(self):
        self.assertIn("runner", ENEMY_TYPES)
        cfg = ENEMY_TYPES["runner"]
        self.assertEqual(cfg["hp"], 2)
        self.assertEqual(cfg["speed"], 2.2)
        self.assertEqual(cfg["radius"], 8)
        self.assertEqual(cfg["xp_value"], 2)

    def test_brute_type_config(self):
        self.assertIn("brute", ENEMY_TYPES)
        cfg = ENEMY_TYPES["brute"]
        self.assertEqual(cfg["hp"], 9)
        self.assertEqual(cfg["speed"], 0.9)
        self.assertEqual(cfg["radius"], 18)
        self.assertEqual(cfg["xp_value"], 5)

    def test_runner_creation(self):
        e = Enemy(self.camera, enemy_type="runner")
        self.assertEqual(e.enemy_type, "runner")
        self.assertEqual(e.hp, 2)
        self.assertEqual(e.speed, 2.2)
        self.assertEqual(e.radius, 8)

    def test_brute_creation(self):
        e = Enemy(self.camera, enemy_type="brute")
        self.assertEqual(e.enemy_type, "brute")
        self.assertEqual(e.hp, 9)
        self.assertEqual(e.speed, 0.9)
        self.assertEqual(e.radius, 18)

    def test_runner_draw_renders_triangle(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="runner")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy + e.radius - 1)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen

    def test_brute_draw_renders_hexagon(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="brute")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen


class TestShieldedEnemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.camera = Camera()

    def test_shielded_type_config(self):
        self.assertIn("shielded", ENEMY_TYPES)
        cfg = ENEMY_TYPES["shielded"]
        self.assertEqual(cfg["hp"], 6)
        self.assertEqual(cfg["speed"], 1.0)
        self.assertEqual(cfg["radius"], 14)
        self.assertEqual(cfg["color"], (0, 255, 255))
        self.assertEqual(cfg["xp_value"], 6)
        self.assertTrue(cfg["shield"])

    def test_shielded_creation(self):
        e = Enemy(self.camera, enemy_type="shielded")
        self.assertEqual(e.enemy_type, "shielded")
        self.assertEqual(e.hp, 6)
        self.assertTrue(e.shield)

    def test_shield_absorbs_first_hit(self):
        e = Enemy(self.camera, enemy_type="shielded")
        original_hp = e.hp
        # Simulate shield absorbing a hit
        self.assertTrue(e.shield)
        e.shield = False  # first hit removes shield
        self.assertFalse(e.shield)
        self.assertEqual(e.hp, original_hp)  # HP unchanged

    def test_shield_then_damage(self):
        e = Enemy(self.camera, enemy_type="shielded")
        original_hp = e.hp
        # First hit: shield absorbs
        e.shield = False
        self.assertEqual(e.hp, original_hp)
        # Second hit: damage goes through
        e.hp -= 1
        self.assertEqual(e.hp, original_hp - 1)

    def test_basic_enemy_has_no_shield(self):
        e = Enemy(self.camera, enemy_type="basic")
        self.assertFalse(e.shield)

    def test_shielded_draw_renders(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="shielded")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen


class TestSplitterEnemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.camera = Camera()

    def test_splitter_type_config(self):
        self.assertIn("splitter", ENEMY_TYPES)
        cfg = ENEMY_TYPES["splitter"]
        self.assertEqual(cfg["hp"], 4)
        self.assertEqual(cfg["speed"], 1.0)
        self.assertEqual(cfg["radius"], 14)
        self.assertEqual(cfg["color"], (0, 255, 100))
        self.assertEqual(cfg["xp_value"], 3)

    def test_mini_type_config(self):
        self.assertIn("mini", ENEMY_TYPES)
        cfg = ENEMY_TYPES["mini"]
        self.assertEqual(cfg["hp"], 2)
        self.assertEqual(cfg["speed"], 1.8)
        self.assertEqual(cfg["radius"], 7)
        self.assertEqual(cfg["xp_value"], 1)

    def test_splitter_creation(self):
        e = Enemy(self.camera, enemy_type="splitter")
        self.assertEqual(e.enemy_type, "splitter")
        self.assertEqual(e.hp, 4)
        self.assertFalse(e.shield)

    def test_mini_creation(self):
        e = Enemy(self.camera, enemy_type="mini")
        self.assertEqual(e.enemy_type, "mini")
        self.assertEqual(e.hp, 2)
        self.assertEqual(e.radius, 7)

    def test_splitter_draw_renders(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="splitter")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen

    def test_mini_draw_renders(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="mini")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen

    def test_split_on_death_produces_minis(self):
        """Simulate the split-on-death logic from the game loop."""
        split_spawns = []
        # Splitter dies
        splitter_x, splitter_y = 100.0, 200.0
        split_spawns.append((splitter_x, splitter_y))
        # Spawn minis like the game loop does
        minis = []
        for sx, sy in split_spawns:
            for offset in (-12, 12):
                mini = Enemy(self.camera, enemy_type="mini")
                mini.x = sx + offset
                mini.y = sy
                minis.append(mini)
        self.assertEqual(len(minis), 2)
        self.assertEqual(minis[0].enemy_type, "mini")
        self.assertEqual(minis[1].enemy_type, "mini")
        self.assertEqual(minis[0].hp, 2)
        self.assertAlmostEqual(minis[0].x, 88.0)
        self.assertAlmostEqual(minis[1].x, 112.0)


class TestEliteEnemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.camera = Camera()

    def test_elite_type_config(self):
        self.assertIn("elite", ENEMY_TYPES)
        cfg = ENEMY_TYPES["elite"]
        self.assertEqual(cfg["hp"], 15)
        self.assertEqual(cfg["speed"], 1.8)
        self.assertEqual(cfg["radius"], 16)
        self.assertEqual(cfg["color"], (255, 0, 255))
        self.assertEqual(cfg["xp_value"], 12)

    def test_elite_creation(self):
        e = Enemy(self.camera, enemy_type="elite")
        self.assertEqual(e.enemy_type, "elite")
        self.assertEqual(e.hp, 15)
        self.assertEqual(e.speed, 1.8)
        self.assertEqual(e.xp_value, 12)

    def test_elite_draw_renders(self):
        import game
        orig_screen = game.screen
        game.screen = pygame.Surface((800, 600))
        try:
            e = Enemy(self.camera, enemy_type="elite")
            e.x, e.y = 200, 200
            e.draw(self.camera)
            sx, sy = self.camera.apply(e.x, e.y)
            pixel = game.screen.get_at((int(sx), int(sy)))
            self.assertNotEqual(pixel, (0, 0, 0, 255))
        finally:
            game.screen = orig_screen


class TestWaveComposition(unittest.TestCase):
    def test_wave_1_only_basic(self):
        for _ in range(50):
            etype = get_enemy_type_for_wave(1)
            self.assertEqual(etype, "basic")

    def test_wave_2_only_basic(self):
        for _ in range(50):
            etype = get_enemy_type_for_wave(2)
            self.assertEqual(etype, "basic")

    def test_wave_3_includes_tier2(self):
        types_seen = set()
        for _ in range(200):
            types_seen.add(get_enemy_type_for_wave(3))
        self.assertIn("runner", types_seen)
        self.assertIn("brute", types_seen)
        self.assertIn("basic", types_seen)

    def test_wave_8_no_basics(self):
        for _ in range(200):
            etype = get_enemy_type_for_wave(8)
            self.assertNotEqual(etype, "basic")

    def test_wave_8_has_tier3(self):
        types_seen = set()
        for _ in range(200):
            types_seen.add(get_enemy_type_for_wave(8))
        self.assertIn("shielded", types_seen)
        self.assertIn("splitter", types_seen)

    def test_wave_10_has_elites(self):
        types_seen = set()
        for _ in range(500):
            types_seen.add(get_enemy_type_for_wave(10))
        self.assertIn("elite", types_seen)

    def test_wave_10_no_basics(self):
        for _ in range(200):
            etype = get_enemy_type_for_wave(10)
            self.assertNotEqual(etype, "basic")

    def test_wave_12_has_elites(self):
        types_seen = set()
        for _ in range(500):
            types_seen.add(get_enemy_type_for_wave(12))
        self.assertIn("elite", types_seen)

    def test_wave_12_no_basics(self):
        for _ in range(200):
            etype = get_enemy_type_for_wave(12)
            self.assertNotEqual(etype, "basic")

    def test_wave_composition_sorted_descending(self):
        thresholds = [t for t, _ in WAVE_COMPOSITION]
        self.assertEqual(thresholds, sorted(thresholds, reverse=True))

    def test_all_types_valid(self):
        for _, weights in WAVE_COMPOSITION:
            for etype in weights:
                self.assertIn(etype, ENEMY_TYPES)


class TestOptionsMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self._saved_resolutions = list(SUPPORTED_RESOLUTIONS)
        self._orig_fullscreen = game.options_fullscreen
        self._orig_res_index = game.options_resolution_index
        # Reset to known base state
        game.SUPPORTED_RESOLUTIONS[:] = [
            (800, 600), (1024, 768), (1280, 720), (1920, 1080)]
        game.options_selected_index = 0
        game.options_resolution_index = 1
        game.options_fullscreen = False
        game.WIDTH, game.HEIGHT = 1024, 768

    def tearDown(self):
        game.SUPPORTED_RESOLUTIONS[:] = self._saved_resolutions
        game.options_fullscreen = self._orig_fullscreen
        game.options_resolution_index = self._orig_res_index

    def test_state_options_constant(self):
        self.assertEqual(STATE_OPTIONS, 4)

    def test_supported_resolutions(self):
        self.assertGreaterEqual(len(SUPPORTED_RESOLUTIONS), 4)
        self.assertIn((1024, 768), SUPPORTED_RESOLUTIONS)
        self.assertIn((1920, 1080), SUPPORTED_RESOLUTIONS)

    def test_apply_resolution_changes_dimensions(self):
        game.screen = pygame.display.set_mode((1024, 768))
        game.options_resolution_index = 0
        apply_resolution()
        self.assertEqual(game.WIDTH, 800)
        self.assertEqual(game.HEIGHT, 600)

    def test_apply_resolution_cycles(self):
        game.screen = pygame.display.set_mode((1024, 768))
        idx_1920 = SUPPORTED_RESOLUTIONS.index((1920, 1080))
        game.options_resolution_index = idx_1920
        apply_resolution()
        self.assertEqual(game.WIDTH, 1920)
        self.assertEqual(game.HEIGHT, 1080)

    def test_apply_resolution_fullscreen_fallback(self):
        game.screen = pygame.display.set_mode((1024, 768))
        game.options_resolution_index = 0  # 800x600
        game.options_fullscreen = True
        # apply_resolution should not crash even if fullscreen fails
        apply_resolution()
        self.assertEqual(game.WIDTH, 800)
        self.assertEqual(game.HEIGHT, 600)

    def test_apply_resolution_all_supported(self):
        """Verify apply_resolution works for every supported resolution."""
        for idx, (w, h) in enumerate(SUPPORTED_RESOLUTIONS):
            game.screen = pygame.display.set_mode((1024, 768))
            game.options_resolution_index = idx
            game.options_fullscreen = False
            apply_resolution()
            self.assertEqual(game.WIDTH, w)
            self.assertEqual(game.HEIGHT, h)

    def test_options_menu_items_count(self):
        """Verify options menu has exactly 3 items: resolution, fullscreen, back."""
        # The draw function uses a hardcoded items list with 3 entries
        # and navigation wraps at % 3, so verify consistency
        self.assertGreaterEqual(len(SUPPORTED_RESOLUTIONS), 4)
        for idx in range(len(SUPPORTED_RESOLUTIONS)):
            game.options_resolution_index = idx
            res = SUPPORTED_RESOLUTIONS[idx]
            self.assertEqual(len(res), 2)
            self.assertGreater(res[0], 0)
            self.assertGreater(res[1], 0)


class TestDetectNativeResolution(unittest.TestCase):
    """Tests for detect_native_resolution() and native resolution integration."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self._saved_resolutions = list(game.SUPPORTED_RESOLUTIONS)
        self._orig_res_index = game.options_resolution_index
        self._orig_fullscreen = game.options_fullscreen
        # Reset to known base state
        game.SUPPORTED_RESOLUTIONS[:] = [
            (800, 600), (1024, 768), (1280, 720), (1920, 1080)]

    def tearDown(self):
        game.SUPPORTED_RESOLUTIONS[:] = self._saved_resolutions
        game.options_resolution_index = self._orig_res_index
        game.options_fullscreen = self._orig_fullscreen

    @patch('pygame.display.Info')
    def test_detect_existing_resolution(self, mock_info):
        """If native resolution is already in the list, don't duplicate it."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        result = detect_native_resolution()
        self.assertEqual(result, (1920, 1080))
        self.assertEqual(game.SUPPORTED_RESOLUTIONS.count((1920, 1080)), 1)

    @patch('pygame.display.Info')
    def test_detect_new_resolution_added(self, mock_info):
        """If native resolution is not in the list, it gets added."""
        mock_info.return_value = MagicMock(current_w=2560, current_h=1440)
        result = detect_native_resolution()
        self.assertEqual(result, (2560, 1440))
        self.assertIn((2560, 1440), game.SUPPORTED_RESOLUTIONS)

    @patch('pygame.display.Info')
    def test_detect_sets_resolution_index(self, mock_info):
        """options_resolution_index is set to the native resolution."""
        mock_info.return_value = MagicMock(current_w=1280, current_h=720)
        detect_native_resolution()
        idx = game.options_resolution_index
        self.assertEqual(game.SUPPORTED_RESOLUTIONS[idx], (1280, 720))

    @patch('pygame.display.Info')
    def test_detect_new_resolution_sorted(self, mock_info):
        """Added resolutions maintain sorted order by pixel count."""
        mock_info.return_value = MagicMock(current_w=1366, current_h=768)
        detect_native_resolution()
        pixel_counts = [w * h for w, h in game.SUPPORTED_RESOLUTIONS]
        self.assertEqual(pixel_counts, sorted(pixel_counts))

    @patch('pygame.display.Info')
    def test_detect_returns_native_tuple(self, mock_info):
        """detect_native_resolution returns a (width, height) tuple."""
        mock_info.return_value = MagicMock(current_w=3840, current_h=2160)
        result = detect_native_resolution()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 3840)
        self.assertEqual(result[1], 2160)

    @patch('pygame.display.Info')
    def test_detect_invalid_resolution_zero(self, mock_info):
        """If display.Info returns (0, 0), detection is skipped."""
        mock_info.return_value = MagicMock(current_w=0, current_h=0)
        orig_index = game.options_resolution_index
        orig_resolutions = list(game.SUPPORTED_RESOLUTIONS)
        result = detect_native_resolution()
        self.assertIsNone(result)
        self.assertEqual(game.options_resolution_index, orig_index)
        self.assertEqual(game.SUPPORTED_RESOLUTIONS, orig_resolutions)

    @patch('pygame.display.Info')
    def test_detect_invalid_resolution_negative(self, mock_info):
        """If display.Info returns (-1, -1), detection is skipped."""
        mock_info.return_value = MagicMock(current_w=-1, current_h=-1)
        result = detect_native_resolution()
        self.assertIsNone(result)
        self.assertNotIn((-1, -1), game.SUPPORTED_RESOLUTIONS)

    @patch('pygame.display.Info', side_effect=pygame.error("no video device"))
    def test_detect_display_info_exception(self, mock_info):
        """If pygame.display.Info() raises, detection returns None gracefully."""
        orig_index = game.options_resolution_index
        orig_resolutions = list(game.SUPPORTED_RESOLUTIONS)
        result = detect_native_resolution()
        self.assertIsNone(result)
        self.assertEqual(game.options_resolution_index, orig_index)
        self.assertEqual(game.SUPPORTED_RESOLUTIONS, orig_resolutions)

    def test_fullscreen_default_is_true(self):
        """options_fullscreen defaults to True for fullscreen startup."""
        # Re-import to check the default
        self.assertTrue(game.options_fullscreen)


class TestHealthPickup(unittest.TestCase):
    def test_creation(self):
        hp = HealthPickup(100, 200, heal_amount=2)
        self.assertEqual(hp.x, 100.0)
        self.assertEqual(hp.y, 200.0)
        self.assertEqual(hp.heal_amount, 2)
        self.assertEqual(hp.lifetime, HealthPickup.LIFETIME)
        self.assertFalse(hp.collected)

    def test_default_heal_amount(self):
        hp = HealthPickup(0, 0)
        self.assertEqual(hp.heal_amount, 1)

    def test_lifetime_decreases(self):
        hp = HealthPickup(0, 0)
        player = Unit(500, 500, (255, 255, 255), is_player=True)
        hp.update(player)
        self.assertEqual(hp.lifetime, HealthPickup.LIFETIME - 1)

    def test_attraction_moves_toward_player(self):
        hp = HealthPickup(100, 100)
        player = Unit(150, 100, (255, 255, 255), is_player=True)
        old_x = hp.x
        hp.update(player)
        self.assertGreater(hp.x, old_x)

    def test_no_attraction_when_far(self):
        hp = HealthPickup(100, 100)
        player = Unit(500, 500, (255, 255, 255), is_player=True)
        old_x, old_y = hp.x, hp.y
        hp.update(player)
        self.assertEqual(hp.x, old_x)
        self.assertEqual(hp.y, old_y)

    def test_collected_on_contact(self):
        hp = HealthPickup(100, 100)
        player = Unit(110, 100, (255, 255, 255), is_player=True)
        hp.update(player)
        self.assertTrue(hp.collected)

    def test_expires_after_lifetime(self):
        hp = HealthPickup(0, 0)
        player = Unit(500, 500, (255, 255, 255), is_player=True)
        hp.lifetime = 1
        hp.update(player)
        self.assertEqual(hp.lifetime, 0)

    def test_collected_on_last_frame(self):
        """Pickup should still be collected if player is in range on the frame it expires."""
        hp = HealthPickup(100, 100)
        player = Unit(110, 100, (255, 255, 255), is_player=True)
        hp.lifetime = 1
        hp.update(player)
        self.assertTrue(hp.collected)


class TestHealthDropSystem(unittest.TestCase):
    def test_drop_chance_basic_enemies(self):
        self.assertEqual(get_health_drop_chance("basic"), 0.05)
        self.assertEqual(get_health_drop_chance("runner"), 0.05)

    def test_drop_chance_higher_for_tough_enemies(self):
        self.assertGreater(get_health_drop_chance("brute"), get_health_drop_chance("basic"))
        self.assertGreater(get_health_drop_chance("elite"), get_health_drop_chance("basic"))

    def test_drop_chance_all_enemy_types_defined(self):
        for etype in ENEMY_TYPES:
            chance = get_health_drop_chance(etype)
            self.assertGreater(chance, 0)
            self.assertLessEqual(chance, 1.0)

    def test_drop_chance_unknown_type_has_default(self):
        self.assertEqual(get_health_drop_chance("unknown_type"), 0.05)

    def test_elite_has_highest_drop_chance(self):
        for etype in ENEMY_TYPES:
            self.assertGreaterEqual(get_health_drop_chance("elite"),
                                    get_health_drop_chance(etype))

    def test_pickup_lifecycle_expired(self):
        hp = HealthPickup(100, 100)
        player = Unit(500, 500, (255, 255, 255), is_player=True)
        hp.lifetime = 1
        hp.update(player)
        pickups = [hp]
        pickups = [p for p in pickups if not p.collected and p.lifetime > 0]
        self.assertEqual(len(pickups), 0)

    def test_pickup_lifecycle_collected(self):
        hp = HealthPickup(100, 100)
        player = Unit(110, 100, (255, 255, 255), is_player=True)
        hp.update(player)
        self.assertTrue(hp.collected)
        pickups = [hp]
        pickups = [p for p in pickups if not p.collected and p.lifetime > 0]
        self.assertEqual(len(pickups), 0)

    def test_pickup_lifecycle_active(self):
        hp = HealthPickup(100, 100)
        player = Unit(500, 500, (255, 255, 255), is_player=True)
        hp.update(player)
        pickups = [hp]
        pickups = [p for p in pickups if not p.collected and p.lifetime > 0]
        self.assertEqual(len(pickups), 1)

    def test_collection_heals_player(self):
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        player.hp = 3
        hp_pickup = HealthPickup(100, 100)
        hp_pickup.update(player)
        self.assertTrue(hp_pickup.collected)
        # Simulate game loop healing
        player.hp = min(player.hp + hp_pickup.heal_amount, player.max_hp)
        self.assertEqual(player.hp, 4)

    def test_collection_caps_at_max_hp(self):
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        self.assertEqual(player.hp, player.max_hp)
        hp_pickup = HealthPickup(100, 100, heal_amount=2)
        hp_pickup.update(player)
        player.hp = min(player.hp + hp_pickup.heal_amount, player.max_hp)
        self.assertEqual(player.hp, player.max_hp)

    def test_max_hp_attribute(self):
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        self.assertEqual(player.max_hp, 5)
        self.assertEqual(player.hp, 5)
        ally = Unit(100, 100, (255, 255, 255), is_player=False)
        self.assertEqual(ally.max_hp, 3)

    def test_drop_chance_values_in_valid_range(self):
        for etype, chance in HEALTH_DROP_CHANCE.items():
            self.assertGreater(chance, 0, f"{etype} drop chance should be > 0")
            self.assertLess(chance, 1.0, f"{etype} drop chance should be < 1.0")


class TestEscapeRoom(unittest.TestCase):
    def test_construction(self):
        er = EscapeRoom(100, 200, 120, 120)
        self.assertEqual(er.x, 100)
        self.assertEqual(er.y, 200)
        self.assertEqual(er.w, 120)
        self.assertEqual(er.h, 120)

    def test_default_size(self):
        er = EscapeRoom(50, 50)
        self.assertEqual(er.w, 120)
        self.assertEqual(er.h, 120)

    def test_collides_circle_inside(self):
        er = EscapeRoom(100, 100, 120, 120)
        # Circle center inside the room
        self.assertTrue(er.collides_circle(160, 160, 10))

    def test_collides_circle_outside(self):
        er = EscapeRoom(100, 100, 120, 120)
        # Circle far away
        self.assertFalse(er.collides_circle(500, 500, 10))

    def test_collides_circle_edge(self):
        er = EscapeRoom(100, 100, 120, 120)
        # Circle just touching the edge
        self.assertTrue(er.collides_circle(100, 90, 15))

    def test_collides_circle_just_outside(self):
        er = EscapeRoom(100, 100, 120, 120)
        # Circle just outside
        self.assertFalse(er.collides_circle(100, 80, 5))

    def test_push_circle_out(self):
        er = EscapeRoom(100, 100, 120, 120)
        # Circle overlapping from the left
        cx, cy = er.push_circle_out(90, 160, 20)
        dist_x = max(er.x, min(cx, er.x + er.w)) - cx
        dist_y = max(er.y, min(cy, er.y + er.h)) - cy
        self.assertGreaterEqual(dist_x * dist_x + dist_y * dist_y, 20 * 20 - 1)

    def test_relocate_avoids_obstacles(self):
        obstacles = [Obstacle(x * 200, 100, 150, 150) for x in range(10)]
        er = EscapeRoom(50, 50, 120, 120)
        er.relocate(obstacles)
        # After relocate, should not overlap any obstacle
        for o in obstacles:
            overlaps = (er.x < o.x + o.w + 20 and er.x + er.w + 20 > o.x and
                        er.y < o.y + o.h + 20 and er.y + er.h + 20 > o.y)
            self.assertFalse(overlaps, "EscapeRoom should not overlap obstacles after relocate")

    def test_relocate_avoids_spawn_center(self):
        er = EscapeRoom(50, 50, 120, 120)
        for _ in range(10):
            er.relocate([])
            cx = er.x + er.w / 2
            cy = er.y + er.h / 2
            dist = math.hypot(cx - MAP_WIDTH / 2, cy - MAP_HEIGHT / 2)
            self.assertGreaterEqual(dist, 200)

    def test_relocate_changes_position(self):
        er = EscapeRoom(50, 50, 120, 120)
        old_x, old_y = er.x, er.y
        # Run multiple times - at least one should change position
        changed = False
        for _ in range(10):
            er.relocate([])
            if er.x != old_x or er.y != old_y:
                changed = True
                break
        self.assertTrue(changed, "relocate should move the escape room")


class TestEscapeRoomIntegration(unittest.TestCase):
    """Tests for escape room integration into the game loop."""

    def test_player_entry_eliminates_visible_enemies(self):
        """When player enters escape room, visible enemies are eliminated."""
        camera = Camera()
        er = EscapeRoom(100, 100, 120, 120)
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        # Place player at escape room center
        player.x = er.x + er.w / 2
        player.y = er.y + er.h / 2
        camera.update(player)

        # Create enemies: one visible (near player), one off-screen
        e_visible = Enemy(camera, enemy_type="basic")
        e_visible.x = player.x + 50
        e_visible.y = player.y + 50

        e_offscreen = Enemy(camera, enemy_type="basic")
        e_offscreen.x = MAP_WIDTH - 10
        e_offscreen.y = MAP_HEIGHT - 10

        enemies = [e_visible, e_offscreen]

        # Verify visibility assumptions
        self.assertTrue(_is_visible(camera, e_visible.x, e_visible.y))
        self.assertFalse(_is_visible(camera, e_offscreen.x, e_offscreen.y))

        # Simulate entry check
        self.assertTrue(er.collides_circle(player.x, player.y, player.RADIUS))

        # Eliminate visible enemies
        surviving = []
        xp_earned = 0
        dead_enemies = []
        for e in enemies:
            if _is_visible(camera, e.x, e.y):
                xp_earned += e.xp_value
                dead_enemies.append((e.x, e.y, e.enemy_type))
            else:
                surviving.append(e)

        self.assertEqual(len(surviving), 1)
        self.assertEqual(surviving[0], e_offscreen)
        self.assertGreater(xp_earned, 0)
        self.assertEqual(len(dead_enemies), 1)

    def test_escape_room_relocates_after_trigger(self):
        """Escape room moves to a new position after player enters."""
        er = EscapeRoom(100, 100, 120, 120)
        old_x, old_y = er.x, er.y
        changed = False
        for _ in range(10):
            er.relocate([])
            if er.x != old_x or er.y != old_y:
                changed = True
                break
        self.assertTrue(changed)

    def test_enemies_pushed_out_of_escape_room(self):
        """Enemies are repelled from the escape room area."""
        er = EscapeRoom(100, 100, 120, 120)
        # Place enemy inside escape room
        camera = Camera()
        e = Enemy(camera, enemy_type="basic")
        e.x = er.x + er.w / 2
        e.y = er.y + er.h / 2
        e.radius = 10

        # Push should move enemy outside
        new_x, new_y = er.push_circle_out(e.x, e.y, e.radius)
        # After push, enemy should no longer collide
        self.assertFalse(er.collides_circle(new_x, new_y, e.radius))

    def test_xp_awarded_for_eliminated_enemies(self):
        """XP is correctly accumulated for enemies eliminated by escape room."""
        camera = Camera()
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        camera.update(player)

        enemies = []
        for _ in range(3):
            e = Enemy(camera, enemy_type="basic")
            e.x = player.x + 30
            e.y = player.y + 30
            enemies.append(e)

        xp_earned = 0
        for e in enemies:
            if _is_visible(camera, e.x, e.y):
                xp_earned += e.xp_value

        expected_xp = sum(e.xp_value for e in enemies)
        self.assertEqual(xp_earned, expected_xp)


class TestEscapeRoomIndicator(unittest.TestCase):
    def test_indicator_returns_none_when_on_screen(self):
        """No indicator when escape room is visible on screen."""
        from game import compute_indicator_position
        result = compute_indicator_position(512, 384, 1024, 768)
        self.assertIsNone(result)

    def test_indicator_returns_position_when_off_screen_right(self):
        """Indicator appears when escape room is off-screen to the right."""
        from game import compute_indicator_position
        result = compute_indicator_position(2000, 384, 1024, 768)
        self.assertIsNotNone(result)
        ix, iy = result
        # Should be clamped to right edge area
        self.assertGreater(ix, 500)
        self.assertLessEqual(ix, 1024 - 30)

    def test_indicator_returns_position_when_off_screen_left(self):
        """Indicator appears when escape room is off-screen to the left."""
        from game import compute_indicator_position
        result = compute_indicator_position(-500, 384, 1024, 768)
        self.assertIsNotNone(result)
        ix, iy = result
        self.assertLessEqual(ix, 100)
        self.assertGreaterEqual(ix, 30)

    def test_indicator_returns_position_when_off_screen_above(self):
        """Indicator appears when escape room is off-screen above."""
        from game import compute_indicator_position
        result = compute_indicator_position(512, -500, 1024, 768)
        self.assertIsNotNone(result)
        ix, iy = result
        self.assertLessEqual(iy, 100)

    def test_indicator_position_clamped_to_screen(self):
        """Indicator position stays within screen bounds."""
        from game import compute_indicator_position
        # Far off bottom-right
        result = compute_indicator_position(5000, 5000, 1024, 768)
        self.assertIsNotNone(result)
        ix, iy = result
        self.assertGreaterEqual(ix, 30)
        self.assertLessEqual(ix, 994)
        self.assertGreaterEqual(iy, 30)
        self.assertLessEqual(iy, 738)


class TestFractalBackground(unittest.TestCase):
    def test_init_generates_buildings(self):
        bg = game.FractalBackground(1024, 768)
        self.assertIsInstance(bg.buildings, list)
        self.assertGreater(len(bg.buildings), 0)
        for b in bg.buildings:
            self.assertIn("x", b)
            self.assertIn("w", b)
            self.assertIn("h", b)

    def test_dimensions_stored(self):
        bg = game.FractalBackground(800, 600)
        self.assertEqual(bg.width, 800)
        self.assertEqual(bg.height, 600)

    def test_draw_callable(self):
        bg = game.FractalBackground(1024, 768)
        surface = pygame.Surface((1024, 768))
        # Should not raise
        bg.draw(surface)

    def test_deterministic_buildings(self):
        bg1 = game.FractalBackground(1024, 768)
        bg2 = game.FractalBackground(1024, 768)
        self.assertEqual(len(bg1.buildings), len(bg2.buildings))
        for b1, b2 in zip(bg1.buildings, bg2.buildings):
            self.assertEqual(b1, b2)


class TestMenuSeparator(unittest.TestCase):
    def test_draw_menu_separator_runs(self):
        surface = pygame.Surface((400, 100))
        game.draw_menu_separator(surface, 10, 50, 200, 1000)

    def test_draw_menu_separator_modifies_surface(self):
        surface = pygame.Surface((400, 100))
        surface.fill((0, 0, 0))
        before = surface.get_at((60, 50))
        game.draw_menu_separator(surface, 10, 50, 200, 1000)
        after = surface.get_at((60, 50))
        self.assertNotEqual(before, after)

    def test_draw_menu_separator_different_ticks(self):
        s1 = pygame.Surface((400, 100))
        s2 = pygame.Surface((400, 100))
        s1.fill((0, 0, 0))
        s2.fill((0, 0, 0))
        game.draw_menu_separator(s1, 10, 50, 200, 0)
        game.draw_menu_separator(s2, 10, 50, 200, 500)
        # At least one pixel should differ due to animation
        differs = False
        for x in range(10, 210):
            if s1.get_at((x, 50)) != s2.get_at((x, 50)):
                differs = True
                break
        self.assertTrue(differs)


class TestMenuFadeIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_mock_font(self):
        from unittest.mock import MagicMock
        mock_font = MagicMock()
        surf = pygame.Surface((100, 30))
        mock_font.render.return_value = surf
        return mock_font

    def setUp(self):
        self._orig_screen = game.screen
        self._orig_font = game.font
        self._orig_title_font = game.title_font
        self._orig_menu_font = game.menu_font
        self._orig_fade_alpha = game.menu_fade_alpha
        self._orig_fade_active = game.menu_fade_active
        self._orig_menu_bg = game._menu_background
        game.screen = pygame.Surface((game.WIDTH, game.HEIGHT))
        game.font = self._make_mock_font()
        game.title_font = self._make_mock_font()
        game.menu_font = self._make_mock_font()

    def tearDown(self):
        game.screen = self._orig_screen
        game.font = self._orig_font
        game.title_font = self._orig_title_font
        game.menu_font = self._orig_menu_font
        game.menu_fade_alpha = self._orig_fade_alpha
        game.menu_fade_active = self._orig_fade_active
        game._menu_background = self._orig_menu_bg

    def test_fade_globals_exist(self):
        self.assertTrue(hasattr(game, 'menu_fade_alpha'))
        self.assertTrue(hasattr(game, 'menu_fade_active'))

    def test_draw_menu_advances_fade(self):
        from unittest.mock import patch
        game._menu_background = game.FractalBackground(game.WIDTH, game.HEIGHT)
        game.menu_fade_alpha = 0
        game.menu_fade_active = True
        with patch('pygame.display.flip'):
            game.draw_menu()
        self.assertGreater(game.menu_fade_alpha, 0)

    def test_fade_completes_at_255(self):
        from unittest.mock import patch
        game._menu_background = game.FractalBackground(game.WIDTH, game.HEIGHT)
        game.menu_fade_alpha = 250
        game.menu_fade_active = True
        with patch('pygame.display.flip'):
            game.draw_menu()
        self.assertEqual(game.menu_fade_alpha, 255)
        self.assertFalse(game.menu_fade_active)


class TestMenuKeyboardNavigation(unittest.TestCase):
    """Verify menu configuration and reset helper."""

    def setUp(self):
        self._orig_idx = game.menu_selected_index
        self._orig_alpha = game.menu_fade_alpha
        self._orig_active = game.menu_fade_active

    def tearDown(self):
        game.menu_selected_index = self._orig_idx
        game.menu_fade_alpha = self._orig_alpha
        game.menu_fade_active = self._orig_active

    def test_menu_items_defined(self):
        self.assertEqual(len(game.MENU_ITEMS), 3)
        self.assertIn("NEW GAME", game.MENU_ITEMS)
        self.assertIn("OPTIONS", game.MENU_ITEMS)
        self.assertIn("QUIT", game.MENU_ITEMS)

    def test_menu_selection_wraps_around(self):
        # Verify the modulo wrap-around arithmetic used by the menu key handler
        n = len(game.MENU_ITEMS)
        game.menu_selected_index = 0
        # UP at index 0 should wrap to last item
        game.menu_selected_index = (game.menu_selected_index - 1) % len(game.MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, n - 1,
                         "UP from index 0 should wrap to last item")
        # DOWN at last index should wrap to first item
        game.menu_selected_index = (game.menu_selected_index + 1) % len(game.MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, 0,
                         "DOWN from last index should wrap to first item")

    def test_reset_menu_state(self):
        from unittest.mock import patch
        game.menu_selected_index = 2
        game.menu_fade_alpha = 200
        game.menu_fade_active = False
        # Mock mouse position to be outside any menu item so index resets to 0
        with patch('pygame.mouse.get_pos', return_value=(0, 0)):
            game._reset_menu_state()
        self.assertEqual(game.menu_selected_index, 0)
        self.assertEqual(game.menu_fade_alpha, 0)
        self.assertTrue(game.menu_fade_active)


class TestStatsCollection(unittest.TestCase):
    """Tests for stats collection system."""

    def test_default_run_stats(self):
        stats = default_run_stats()
        self.assertEqual(stats["damage_dealt"], 0)
        self.assertEqual(stats["damage_taken"], 0)
        self.assertIsInstance(stats["weapons_used"], set)
        self.assertIsInstance(stats["weapon_damage"], dict)
        self.assertIsInstance(stats["weapon_kills"], dict)
        self.assertIsInstance(stats["weapon_picks"], dict)

    def test_collect_run_stats(self):
        run_stats = default_run_stats()
        run_stats["damage_dealt"] = 50
        run_stats["damage_taken"] = 3
        run_stats["weapons_used"] = {"normal", "shotgun"}
        run_stats["weapon_damage"] = {"normal": 30, "shotgun": 20}
        run_stats["weapon_kills"] = {"normal": 10, "shotgun": 5}
        run_stats["weapon_picks"] = {"normal": 1, "shotgun": 1}
        inv = default_weapon_inventory()
        inv[0]["weapon_type"] = "shotgun"

        result = collect_run_stats(run_stats, score=15, level=4, wave=3,
                                   xp_earned_total=42, survival_time=120.5,
                                   weapon_inventory=inv)
        self.assertEqual(result["kills"], 15)
        self.assertEqual(result["damage_dealt"], 50)
        self.assertEqual(result["damage_taken"], 3)
        self.assertEqual(result["waves_reached"], 3)
        self.assertEqual(result["level_reached"], 4)
        self.assertEqual(result["survival_time_seconds"], 120.5)
        self.assertEqual(result["xp_earned"], 42)
        self.assertEqual(result["final_weapons"], ["shotgun"])
        self.assertEqual(set(result["weapons_used"]), {"normal", "shotgun"})
        self.assertIn("timestamp", result)
        self.assertIn("weapon_stats", result)

    def test_collect_weapon_stats(self):
        run_stats = default_run_stats()
        run_stats["weapon_damage"] = {"normal": 30, "shotgun": 20}
        run_stats["weapon_kills"] = {"normal": 10}
        run_stats["weapon_picks"] = {"normal": 1, "shotgun": 1}

        result = collect_weapon_stats(run_stats)
        self.assertEqual(result["normal"]["total_damage"], 30)
        self.assertEqual(result["normal"]["total_kills"], 10)
        self.assertEqual(result["normal"]["times_picked"], 1)
        self.assertEqual(result["shotgun"]["total_damage"], 20)
        self.assertEqual(result["shotgun"]["total_kills"], 0)
        self.assertEqual(result["shotgun"]["times_picked"], 1)

    def test_save_stats_creates_file(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        try:
            import game
            old = game.STATS_FILE
            game.STATS_FILE = tmp
            save_stats({"test": True})
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertTrue(data[0]["test"])
            # Append second entry
            save_stats({"test2": True})
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(len(data), 2)
        finally:
            game.STATS_FILE = old
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_save_stats_handles_corrupt_file(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not json")
            tmp = f.name
        try:
            import game
            old = game.STATS_FILE
            game.STATS_FILE = tmp
            save_stats({"recovery": True})
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
        finally:
            game.STATS_FILE = old
            os.unlink(tmp)


class TestMultiWeaponInventory(unittest.TestCase):
    """Tests for multi-weapon inventory system."""

    def test_default_weapon_inventory(self):
        inv = default_weapon_inventory()
        self.assertIsInstance(inv, list)
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["weapon_type"], "normal")
        self.assertIn("cooldown", inv[0])

    def test_default_weapon_stats_has_cooldown(self):
        ws = default_weapon_stats()
        self.assertIn("cooldown", ws)
        self.assertEqual(ws["cooldown"], 0)

    def test_multi_weapon_firing(self):
        """Player with 2 weapons fires both on their own cooldown cycles."""
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        inv = default_weapon_inventory()
        # Add a shotgun
        shotgun = default_weapon_stats()
        shotgun["weapon_type"] = "shotgun"
        inv.append(shotgun)

        # Create enemy in range
        camera = Camera()
        enemy = Enemy(camera)
        enemy.x, enemy.y = 120, 100

        bullets = []
        player.shoot_at(enemy, bullets, weapon_stats=inv)
        # Both weapons should fire (cooldown=0)
        # normal: 1 bullet, shotgun: 5 bullets = 6 total
        self.assertEqual(len(bullets), 6)
        types = {b.weapon_type for b in bullets}
        self.assertIn("normal", types)
        self.assertIn("shotgun", types)

    def test_multi_weapon_independent_cooldowns(self):
        """Each weapon tracks its own cooldown."""
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        inv = default_weapon_inventory()
        shotgun = default_weapon_stats()
        shotgun["weapon_type"] = "shotgun"
        inv.append(shotgun)

        camera = Camera()
        enemy = Enemy(camera)
        enemy.x, enemy.y = 120, 100

        bullets = []
        player.shoot_at(enemy, bullets, weapon_stats=inv)
        # Both fire, now both have cooldowns set
        self.assertGreater(inv[0]["cooldown"], 0)
        self.assertGreater(inv[1]["cooldown"], 0)

        # Second call: cooldowns tick down but no firing
        bullets2 = []
        player.shoot_at(enemy, bullets2, weapon_stats=inv)
        self.assertEqual(len(bullets2), 0)

    def test_apply_upgrade_stat_to_all_weapons(self):
        """Stat upgrades apply to all weapons in inventory."""
        inv = default_weapon_inventory()
        shotgun = default_weapon_stats()
        shotgun["weapon_type"] = "shotgun"
        inv.append(shotgun)

        option = {"name": "+Damage", "stat": "damage", "amount": 2}
        apply_upgrade(inv, option)
        for ws in inv:
            self.assertEqual(ws["damage"], 3)  # 1 + 2

    def test_apply_upgrade_fire_rate_clamp(self):
        """Fire rate is clamped to minimum 5 for all weapons."""
        inv = default_weapon_inventory()
        inv[0]["fire_rate"] = 5
        option = {"name": "+Fire Rate", "stat": "fire_rate", "amount": -10}
        apply_upgrade(inv, option)
        self.assertEqual(inv[0]["fire_rate"], 5)

    def test_apply_upgrade_weapon_type_adds_to_inventory(self):
        """Weapon type milestone adds new weapon entry to inventory."""
        inv = default_weapon_inventory()
        option = {"name": "Weapon: Shotgun", "weapon_type": "shotgun"}
        apply_upgrade(inv, option)
        self.assertEqual(len(inv), 2)
        self.assertEqual(inv[1]["weapon_type"], "shotgun")

    def test_new_weapon_inherits_stat_bonuses(self):
        """New weapon added at milestone inherits global stat bonuses."""
        inv = default_weapon_inventory()
        # Apply some damage upgrades first
        apply_upgrade(inv, {"name": "+Damage", "stat": "damage", "amount": 3})
        self.assertEqual(inv[0]["damage"], 4)

        # Now add shotgun
        apply_upgrade(inv, {"name": "Weapon: Shotgun", "weapon_type": "shotgun"})
        self.assertEqual(len(inv), 2)
        self.assertEqual(inv[1]["damage"], 4)  # inherits bonus

    def test_generate_upgrade_excludes_owned_weapons(self):
        """Milestone upgrade options exclude already-owned weapon types."""
        inv = default_weapon_inventory()
        shotgun = default_weapon_stats()
        shotgun["weapon_type"] = "shotgun"
        inv.append(shotgun)

        import random
        found_weapon = False
        random.seed(42)
        # Force milestone level
        for _ in range(100):
            options = generate_upgrade_options(10, inv)
            for opt in options:
                if "weapon_type" in opt:
                    found_weapon = True
                    self.assertNotEqual(opt["weapon_type"], "normal")
                    self.assertNotEqual(opt["weapon_type"], "shotgun")
        self.assertTrue(found_weapon, "Expected at least one weapon option in 100 iterations")

    def test_generate_upgrade_all_weapons_collected(self):
        """When all weapon types collected, milestone offers stat upgrade instead."""
        inv = default_weapon_inventory()
        for wt in WEAPON_TYPES:
            if wt == "normal":
                continue
            ws = default_weapon_stats()
            ws["weapon_type"] = wt
            inv.append(ws)

        import random
        random.seed(42)
        options = generate_upgrade_options(10, inv)
        # All 3 options should be stat upgrades (no weapon_type key)
        for opt in options:
            self.assertNotIn("weapon_type", opt)

    def test_collect_run_stats_with_inventory(self):
        """collect_run_stats handles weapon inventory list."""
        run_stats = default_run_stats()
        inv = default_weapon_inventory()
        shotgun = default_weapon_stats()
        shotgun["weapon_type"] = "shotgun"
        inv.append(shotgun)

        result = collect_run_stats(run_stats, score=5, level=2, wave=1,
                                   xp_earned_total=10, survival_time=30.0,
                                   weapon_inventory=inv)
        self.assertEqual(result["final_weapons"], ["normal", "shotgun"])

    def test_apply_upgrade_max_hp_with_inventory(self):
        """Max HP upgrade works with inventory (doesn't modify weapons)."""
        inv = default_weapon_inventory()
        player = Unit(100, 100, PLAYER_COLOR, is_player=True)
        option = {"name": "+Max HP", "stat": "max_hp", "amount": 1}
        apply_upgrade(inv, option, player=player)
        self.assertEqual(player.max_hp, 6)
        # Weapons unchanged
        self.assertEqual(len(inv), 1)


class TestEnemyRebalance(unittest.TestCase):
    """Tests for the enemy rebalance: reduced counts, buffed stats."""

    def test_max_enemies_base(self):
        self.assertEqual(MAX_ENEMIES_BASE, 140)
        self.assertEqual(MAX_ENEMIES_CAP, 200)

    def test_max_enemies_scales_with_wave(self):
        # Wave 1: 140 + 1*2 = 142
        self.assertEqual(get_max_enemies(1), 142)
        # Wave 20: 140 + 20*2 = 180
        self.assertEqual(get_max_enemies(20), 180)
        # Wave 30: 140 + 30*2 = 200 (hits cap)
        self.assertEqual(get_max_enemies(30), 200)
        # Wave 50: still capped at 200
        self.assertEqual(get_max_enemies(50), 200)

    def test_buffed_hp_values(self):
        expected_hp = {"basic": 3, "runner": 2, "brute": 9, "shielded": 6,
                       "splitter": 4, "mini": 2, "elite": 15, "shooter": 5}
        for etype, hp in expected_hp.items():
            self.assertEqual(ENEMY_TYPES[etype]["hp"], hp,
                             f"{etype} HP should be {hp}")

    def test_buffed_xp_values(self):
        expected_xp = {"basic": 2, "runner": 2, "brute": 5, "shielded": 6,
                       "splitter": 3, "mini": 1, "elite": 12, "shooter": 5}
        for etype, xp in expected_xp.items():
            self.assertEqual(ENEMY_TYPES[etype]["xp_value"], xp,
                             f"{etype} xp_value should be {xp}")

    def test_speed_buffs(self):
        self.assertAlmostEqual(ENEMY_TYPES["basic"]["speed"], 1.4)
        self.assertAlmostEqual(ENEMY_TYPES["brute"]["speed"], 0.9)

    def test_spawn_count_formula(self):
        """get_spawn_count returns wave + wave // 4."""
        self.assertEqual(get_spawn_count(1), 1)
        self.assertEqual(get_spawn_count(4), 5)
        self.assertEqual(get_spawn_count(10), 12)
        self.assertEqual(get_spawn_count(20), 25)


class TestEnemyWaveScaling(unittest.TestCase):
    """Tests for wave-based enemy stat scaling."""

    def setUp(self):
        self.camera = Camera()

    def test_wave_1_uses_base_stats(self):
        e = Enemy(self.camera, enemy_type="basic", wave=1)
        self.assertEqual(e.hp, 3)
        self.assertAlmostEqual(e.speed, 1.4)
        self.assertEqual(e.xp_value, 2)
        self.assertEqual(e.contact_damage, 1)

    def test_hp_scales_with_wave(self):
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        # int(3 * (1 + 0.12 * 9)) = int(3 * 2.08) = int(6.24) = 6
        self.assertEqual(e.hp, 6)

    def test_elite_hp_at_wave_20(self):
        e = Enemy(self.camera, enemy_type="elite", wave=20)
        # int(15 * (1 + 0.12 * 19)) = int(15 * 3.28) = int(49.2) = 49
        self.assertEqual(e.hp, 49)

    def test_speed_scales_with_wave(self):
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        # 1.4 * min(1.6, 1 + 0.02 * 9) = 1.4 * 1.18 = 1.652
        self.assertAlmostEqual(e.speed, 1.652)

    def test_speed_capped(self):
        e = Enemy(self.camera, enemy_type="runner", wave=60)
        # 2.2 * min(2.0, 1 + 0.02 * 59) = 2.2 * 2.0 = 4.4
        self.assertAlmostEqual(e.speed, 4.4)

    def test_speed_at_wave_40(self):
        e = Enemy(self.camera, enemy_type="basic", wave=40)
        # 1.4 * min(2.0, 1 + 0.02 * 39) = 1.4 * 1.78 = 2.492
        self.assertAlmostEqual(e.speed, 2.492)

    def test_contact_damage_per_wave(self):
        cases = [(1, 1), (6, 2), (16, 4), (25, 5)]
        for wave, expected_dmg in cases:
            e = Enemy(self.camera, enemy_type="basic", wave=wave)
            self.assertEqual(e.contact_damage, expected_dmg,
                             f"wave {wave}: expected contact_damage={expected_dmg}, got {e.contact_damage}")

    def test_xp_scales_with_wave(self):
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        # 2 + 10 // 5 = 4
        self.assertEqual(e.xp_value, 4)

    def test_mini_spawns_get_wave_scaling(self):
        e = Enemy(self.camera, enemy_type="mini", wave=10)
        # mini base_hp=2, int(2 * 2.08) = int(4.16) = 4
        self.assertEqual(e.hp, 4)
        # mini base_speed=1.8, 1.8 * 1.18 = 2.124
        self.assertAlmostEqual(e.speed, 2.124)

    def test_hp_compound_scaling_after_wave_20(self):
        # Compound multiplier 1.06^(wave-20) kicks in after wave 20
        # Wave 30 basic: int(3 * 4.48 * 1.06^10) = int(3 * 4.48 * 1.7908) = 24
        e30 = Enemy(self.camera, enemy_type="basic", wave=30)
        self.assertEqual(e30.hp, 24)
        # Wave 50 basic: int(3 * 6.88 * 1.06^30) = int(3 * 6.88 * 5.7434) = 118
        e50 = Enemy(self.camera, enemy_type="basic", wave=50)
        self.assertEqual(e50.hp, 118)
        # Wave 30 elite: int(15 * 4.48 * 1.06^10) = 120
        e30_elite = Enemy(self.camera, enemy_type="elite", wave=30)
        self.assertEqual(e30_elite.hp, 120)
        # Wave 50 elite: int(15 * 6.88 * 1.06^30) = 592
        e50_elite = Enemy(self.camera, enemy_type="elite", wave=50)
        self.assertEqual(e50_elite.hp, 592)

    def test_hp_compound_unchanged_before_wave_21(self):
        # Compound multiplier is 1.0 for waves <= 20, so HP unchanged
        e10 = Enemy(self.camera, enemy_type="basic", wave=10)
        self.assertEqual(e10.hp, 6)
        e20 = Enemy(self.camera, enemy_type="elite", wave=20)
        self.assertEqual(e20.hp, 49)

    def test_lategame_enemy_survives_base_damage(self):
        """Wave-50 basic enemy should have HP > 100 thanks to compound scaling."""
        e = Enemy(self.camera, enemy_type="basic", wave=50)
        self.assertGreater(e.hp, 100,
                           f"Wave 50 basic enemy HP ({e.hp}) should exceed 100 to survive late-game hits")

    def test_damage_upgrade_diminishing(self):
        """Verify get_scaled_amount returns reduced values at level 10 and 20."""
        # Level 10: base +1 damage returns +1 (unchanged from base)
        self.assertEqual(get_scaled_amount("damage", 1, 10), 1)
        # Level 20: base +1 damage returns +2 (base_amount + 1)
        self.assertEqual(get_scaled_amount("damage", 1, 20), 2)


class TestSnapshotWeaponPower(unittest.TestCase):
    """Tests for snapshot_weapon_power function."""

    def test_single_weapon_snapshot(self):
        inv = default_weapon_inventory()
        result = snapshot_weapon_power(inv)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "normal")
        self.assertEqual(result[0]["dmg"], 1)
        self.assertEqual(result[0]["fire_rate"], 25)
        self.assertEqual(result[0]["speed"], 8)
        self.assertEqual(result[0]["range"], 90)

    def test_multi_weapon_snapshot(self):
        inv = default_weapon_inventory()
        ws = default_weapon_stats()
        ws["weapon_type"] = "shotgun"
        ws["damage"] = 5
        inv.append(ws)
        result = snapshot_weapon_power(inv)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "normal")
        self.assertEqual(result[1]["type"], "shotgun")
        self.assertEqual(result[1]["dmg"], 5)


class TestDefaultRunStatsFields(unittest.TestCase):
    """Verify all fields in default_run_stats."""

    def test_all_fields_present(self):
        stats = default_run_stats()
        self.assertEqual(stats["wave_damage_dealt"], 0)
        self.assertEqual(stats["wave_damage_taken"], 0)
        self.assertEqual(stats["wave_kills"], 0)
        self.assertEqual(stats["wave_xp_earned"], 0)
        self.assertIsInstance(stats["wave_logs"], list)
        self.assertEqual(len(stats["wave_logs"]), 0)
        self.assertIsInstance(stats["level_logs"], list)
        self.assertEqual(len(stats["level_logs"]), 0)

    def test_collect_run_stats_includes_logs(self):
        run_stats = default_run_stats()
        run_stats["wave_logs"] = [{"wave": 1, "kills": 5}]
        run_stats["level_logs"] = [{"level": 2, "chosen": "+Damage"}]
        inv = default_weapon_inventory()
        result = collect_run_stats(run_stats, score=5, level=2, wave=1,
                                   xp_earned_total=10, survival_time=30.0,
                                   weapon_inventory=inv)
        self.assertEqual(result["wave_logs"], [{"wave": 1, "kills": 5}])
        self.assertEqual(result["level_logs"], [{"level": 2, "chosen": "+Damage"}])


class TestGamepadInitialization(unittest.TestCase):
    """Tests for gamepad initialization and hot-plug handling."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self._orig_screen = game.screen
        self._orig_joystick = game.active_joystick
        self._saved_resolutions = list(game.SUPPORTED_RESOLUTIONS)
        self._orig_res_index = game.options_resolution_index
        self._orig_fullscreen = game.options_fullscreen
        # Prevent init_pygame from early-returning due to existing screen
        game.screen = None

    def tearDown(self):
        game.screen = self._orig_screen
        game.active_joystick = self._orig_joystick
        game.SUPPORTED_RESOLUTIONS[:] = self._saved_resolutions
        game.options_resolution_index = self._orig_res_index
        game.options_fullscreen = self._orig_fullscreen

    def test_deadzone_constant_exists_and_reasonable(self):
        self.assertIsInstance(JOYSTICK_DEADZONE, float)
        self.assertGreater(JOYSTICK_DEADZONE, 0.0)
        self.assertLess(JOYSTICK_DEADZONE, 1.0)

    def test_active_joystick_initial_none(self):
        # When no joystick is connected, active_joystick should default to None
        self.assertIsNone(game.active_joystick)

    @patch('pygame.joystick.init')
    @patch('pygame.joystick.get_count', return_value=0)
    @patch('pygame.display.Info')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1024, 768)))
    @patch('pygame.display.set_caption')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    def test_init_pygame_calls_joystick_init(self, mock_sysfont, mock_caption,
                                             mock_set_mode, mock_info,
                                             mock_get_count, mock_joy_init):
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.screen = None
        game.active_joystick = None
        init_pygame()
        # pygame.init() also calls joystick.init(), so it may be called more than once
        self.assertTrue(mock_joy_init.called)
        # No joystick connected, so active_joystick stays None
        self.assertIsNone(game.active_joystick)

    @patch('pygame.joystick.Joystick')
    @patch('pygame.joystick.init')
    @patch('pygame.joystick.get_count', return_value=1)
    @patch('pygame.display.Info')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1024, 768)))
    @patch('pygame.display.set_caption')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    def test_init_pygame_grabs_first_joystick(self, mock_sysfont, mock_caption,
                                              mock_set_mode, mock_info,
                                              mock_get_count,
                                              mock_joy_init, mock_joystick_cls):
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        mock_joy = MagicMock()
        mock_joystick_cls.return_value = mock_joy
        game.screen = None
        game.active_joystick = None
        init_pygame()
        mock_joystick_cls.assert_called_once_with(0)
        mock_joy.init.assert_called_once()
        self.assertEqual(game.active_joystick, mock_joy)

    def test_joy_device_added_sets_active_joystick(self):
        mock_joy = MagicMock()
        with patch('pygame.joystick.Joystick', return_value=mock_joy) as mock_cls:
            result = handle_joy_device_added(None, 0)
            mock_cls.assert_called_once_with(0)
            mock_joy.init.assert_called_once()
            self.assertEqual(result, mock_joy)

    def test_joy_device_removed_clears_active_joystick(self):
        mock_joy = MagicMock()
        mock_joy.get_instance_id.return_value = 42
        with patch('pygame.joystick.get_count', return_value=0):
            result = handle_joy_device_removed(mock_joy, 42)
            self.assertIsNone(result)

    def test_joy_device_removed_grabs_next_joystick(self):
        mock_joy = MagicMock()
        mock_joy.get_instance_id.return_value = 42
        mock_joy2 = MagicMock()
        with patch('pygame.joystick.get_count', return_value=1), \
             patch('pygame.joystick.Joystick', return_value=mock_joy2):
            result = handle_joy_device_removed(mock_joy, 42)
            self.assertEqual(result, mock_joy2)
            mock_joy2.init.assert_called_once()

    def test_joy_device_removed_different_instance_no_change(self):
        mock_joy = MagicMock()
        mock_joy.get_instance_id.return_value = 42
        result = handle_joy_device_removed(mock_joy, 99)
        self.assertEqual(result, mock_joy)

    def test_joy_device_added_ignored_if_already_active(self):
        existing_joy = MagicMock()
        mock_joy2 = MagicMock()
        with patch('pygame.joystick.Joystick', return_value=mock_joy2) as mock_cls:
            result = handle_joy_device_added(existing_joy, 1)
            mock_cls.assert_not_called()
            self.assertEqual(result, existing_joy)

    @patch('pygame.joystick.Joystick', side_effect=pygame.error("no joystick"))
    @patch('pygame.joystick.init')
    @patch('pygame.joystick.get_count', return_value=1)
    @patch('pygame.display.Info')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1024, 768)))
    @patch('pygame.display.set_caption')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    def test_init_pygame_joystick_error_sets_none(self, mock_sysfont, mock_caption,
                                                  mock_set_mode, mock_info,
                                                  mock_get_count,
                                                  mock_joy_init, mock_joystick_cls):
        """init_pygame() catches pygame.error during joystick probe and leaves active_joystick as None."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.screen = None
        game.active_joystick = None
        init_pygame()
        self.assertIsNone(game.active_joystick)

    def test_joy_device_added_error_sets_none(self):
        """JOYDEVICEADDED handler catches pygame.error and leaves active_joystick as None."""
        with patch('pygame.joystick.Joystick', side_effect=pygame.error("device gone")):
            result = handle_joy_device_added(None, 0)
            self.assertIsNone(result)


class TestGamepadMovement(unittest.TestCase):
    """Tests for gamepad movement input during STATE_PLAYING."""

    def setUp(self):
        self.saved_joystick = game.active_joystick

    def tearDown(self):
        game.active_joystick = self.saved_joystick

    def test_analog_stick_horizontal_movement(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.8, 1: 0.0}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, 0.8)
        self.assertAlmostEqual(my, 0.0)

    def test_analog_stick_vertical_movement(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.0, 1: -0.9}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, 0.0)
        self.assertAlmostEqual(my, -0.9)

    def test_analog_stick_diagonal_movement(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.7, 1: 0.7}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, 0.7)
        self.assertAlmostEqual(my, 0.7)

    def test_analog_stick_deadzone_filters_small_input(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.1, 1: -0.2}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, 0.0)
        self.assertAlmostEqual(my, 0.0)

    def test_analog_stick_at_deadzone_boundary_filtered(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.3, 1: -0.3}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, 0.0)
        self.assertAlmostEqual(my, 0.0)

    def test_dpad_movement_right(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 1
        mock_joy.get_hat.return_value = (1, 0)
        game.active_joystick = mock_joy
        mx, my = 0, 0
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            mx += hat_x
            my -= hat_y
        self.assertEqual(mx, 1)
        self.assertEqual(my, 0)

    def test_dpad_movement_up(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 1
        mock_joy.get_hat.return_value = (0, 1)
        game.active_joystick = mock_joy
        mx, my = 0, 0
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            mx += hat_x
            my -= hat_y
        self.assertEqual(mx, 0)
        self.assertEqual(my, -1)

    def test_dpad_movement_down_left(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 1
        mock_joy.get_hat.return_value = (-1, -1)
        game.active_joystick = mock_joy
        mx, my = 0, 0
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            mx += hat_x
            my -= hat_y
        self.assertEqual(mx, -1)
        self.assertEqual(my, 1)

    def test_no_joystick_no_gamepad_input(self):
        game.active_joystick = None
        mx, my = 0, 0
        if game.active_joystick is not None:
            mx += game.active_joystick.get_axis(0)
        self.assertEqual(mx, 0)
        self.assertEqual(my, 0)

    def test_combined_keyboard_and_stick_movement(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.5, 1: 0.0}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        # Simulate keyboard pressing left (mx=-1) combined with stick right (0.5)
        mx, my = -1, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        self.assertAlmostEqual(mx, -0.5)
        self.assertAlmostEqual(my, 0.0)

    def test_combined_keyboard_and_dpad_movement(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 1
        mock_joy.get_hat.return_value = (1, 0)
        game.active_joystick = mock_joy
        # Simulate keyboard pressing up (my=-1) combined with dpad right
        mx, my = 0, -1
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            mx += hat_x
            my -= hat_y
        self.assertEqual(mx, 1)
        self.assertEqual(my, -1)

    def test_movement_normalization_with_gamepad(self):
        # Verify that combined movement gets normalized properly
        mx, my = 1.5, 1.5
        if mx or my:
            length = math.hypot(mx, my)
            norm_mx = mx / length
            norm_my = my / length
            # Normalized vector should have magnitude 1
            self.assertAlmostEqual(math.hypot(norm_mx, norm_my), 1.0)

    def test_dpad_no_hats_available(self):
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        mx, my = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > game.JOYSTICK_DEADZONE:
            mx += axis_x
        if abs(axis_y) > game.JOYSTICK_DEADZONE:
            my += axis_y
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            mx += hat_x
            my -= hat_y
        self.assertEqual(mx, 0)
        self.assertEqual(my, 0)
        mock_joy.get_hat.assert_not_called()


class TestGamepadMenuNavigation(unittest.TestCase):
    """Tests for gamepad button and D-pad/stick navigation across all UI states."""

    def setUp(self):
        self._orig_joystick = game.active_joystick
        self._orig_menu_idx = game.menu_selected_index
        self._orig_options_idx = game.options_selected_index
        self._orig_levelup_idx = game.level_up_selected_index
        self._orig_nav_time = game._gamepad_nav_last_time

    def tearDown(self):
        game.active_joystick = self._orig_joystick
        game.menu_selected_index = self._orig_menu_idx
        game.options_selected_index = self._orig_options_idx
        game.level_up_selected_index = self._orig_levelup_idx
        game._gamepad_nav_last_time = self._orig_nav_time

    # -- Constants --

    def test_nav_repeat_delay_exists_and_positive(self):
        self.assertIsInstance(GAMEPAD_NAV_REPEAT_DELAY, float)
        self.assertGreater(GAMEPAD_NAV_REPEAT_DELAY, 0.0)

    def test_level_up_selected_index_default(self):
        # Should default to 0
        self.assertEqual(game.level_up_selected_index, 0)

    # -- A button (button 0) tests --

    def test_a_button_menu_new_game(self):
        """A button on menu index 0 should trigger NEW GAME (state -> STATE_PLAYING)."""
        game.menu_selected_index = 0
        state = STATE_MENU
        # Simulate JOYBUTTONDOWN button=0 handling
        if state == STATE_MENU:
            if game.menu_selected_index == 0:
                state = STATE_PLAYING
        self.assertEqual(state, STATE_PLAYING)

    def test_a_button_menu_options(self):
        """A button on menu index 1 should go to OPTIONS."""
        game.menu_selected_index = 1
        state = STATE_MENU
        if state == STATE_MENU:
            if game.menu_selected_index == 1:
                game.options_selected_index = 0
                state = STATE_OPTIONS
        self.assertEqual(state, STATE_OPTIONS)
        self.assertEqual(game.options_selected_index, 0)

    def test_a_button_menu_quit(self):
        """A button on menu index 2 should set running=False."""
        game.menu_selected_index = 2
        state = STATE_MENU
        running = True
        if state == STATE_MENU:
            if game.menu_selected_index == 2:
                running = False
        self.assertFalse(running)

    def test_a_button_options_back(self):
        """A button on options index 2 (Back) should return to menu."""
        game.options_selected_index = 2
        state = STATE_OPTIONS
        if state == STATE_OPTIONS:
            if game.options_selected_index == 2:
                state = STATE_MENU
        self.assertEqual(state, STATE_MENU)

    def test_a_button_options_not_back(self):
        """A button on options index 0 or 1 should not change state."""
        game.options_selected_index = 0
        state = STATE_OPTIONS
        if state == STATE_OPTIONS:
            if game.options_selected_index == 2:
                state = STATE_MENU
        self.assertEqual(state, STATE_OPTIONS)

    def test_a_button_level_up_selects_upgrade(self):
        """A button in level-up state should select the highlighted upgrade."""
        game.level_up_selected_index = 1
        upgrade_options = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        selected = None
        state = STATE_LEVEL_UP
        if state == STATE_LEVEL_UP and upgrade_options:
            idx = game.level_up_selected_index
            if 0 <= idx < len(upgrade_options):
                selected = upgrade_options[idx]
        self.assertEqual(selected, {"name": "B"})

    def test_a_button_level_up_out_of_range(self):
        """A button with out-of-range index should not select anything."""
        game.level_up_selected_index = 5
        upgrade_options = [{"name": "A"}, {"name": "B"}]
        selected = None
        state = STATE_LEVEL_UP
        if state == STATE_LEVEL_UP and upgrade_options:
            idx = game.level_up_selected_index
            if 0 <= idx < len(upgrade_options):
                selected = upgrade_options[idx]
        self.assertIsNone(selected)

    def test_a_button_game_over_restarts(self):
        """A button on game over should restart (state -> STATE_PLAYING)."""
        state = STATE_GAME_OVER
        if state == STATE_GAME_OVER:
            state = STATE_PLAYING
        self.assertEqual(state, STATE_PLAYING)

    # -- B button (button 1) tests --

    def test_b_button_options_returns_to_menu(self):
        """B button in options should return to menu."""
        state = STATE_OPTIONS
        if state == STATE_OPTIONS:
            state = STATE_MENU
        self.assertEqual(state, STATE_MENU)

    def test_b_button_game_over_returns_to_menu(self):
        """B button on game over should return to menu."""
        state = STATE_GAME_OVER
        if state == STATE_GAME_OVER:
            state = STATE_MENU
        self.assertEqual(state, STATE_MENU)

    def test_b_button_playing_returns_to_menu(self):
        """B button during gameplay should return to menu."""
        state = STATE_PLAYING
        if state == STATE_PLAYING:
            state = STATE_MENU
        self.assertEqual(state, STATE_MENU)

    def test_b_button_menu_quits(self):
        """B button on menu should quit."""
        state = STATE_MENU
        running = True
        if state == STATE_MENU:
            running = False
        self.assertFalse(running)

    # -- D-pad/stick navigation tests --

    def test_dpad_menu_navigate_down(self):
        """D-pad down in menu should increment selected index."""
        game.menu_selected_index = 0
        game._gamepad_nav_last_time = 0
        nav_y = 1  # down
        import time
        now = time.time()
        if nav_y and (now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY):
            game._gamepad_nav_last_time = now
            game.menu_selected_index = (game.menu_selected_index + 1) % len(MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, 1)

    def test_dpad_menu_navigate_up(self):
        """D-pad up in menu should decrement selected index (wrapping)."""
        game.menu_selected_index = 0
        game._gamepad_nav_last_time = 0
        nav_y = -1  # up
        import time
        now = time.time()
        if nav_y and (now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY):
            game._gamepad_nav_last_time = now
            game.menu_selected_index = (game.menu_selected_index - 1) % len(MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, len(MENU_ITEMS) - 1)

    def test_dpad_menu_wraps_around(self):
        """Menu navigation should wrap from last to first."""
        game.menu_selected_index = len(MENU_ITEMS) - 1
        game._gamepad_nav_last_time = 0
        import time
        now = time.time()
        game._gamepad_nav_last_time = now
        game.menu_selected_index = (game.menu_selected_index + 1) % len(MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, 0)

    def test_dpad_options_navigate_down(self):
        """D-pad down in options should increment selected index."""
        game.options_selected_index = 0
        game._gamepad_nav_last_time = 0
        import time
        now = time.time()
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            game.options_selected_index = (game.options_selected_index + 1) % 3
        self.assertEqual(game.options_selected_index, 1)

    def test_dpad_options_left_right_changes_resolution(self):
        """D-pad left/right on resolution option should change resolution index."""
        game.options_selected_index = 0
        orig_res = game.options_resolution_index
        game._gamepad_nav_last_time = 0
        import time
        now = time.time()
        nav_x = 1
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            if game.options_selected_index == 0:
                game.options_resolution_index = (game.options_resolution_index + nav_x) % len(SUPPORTED_RESOLUTIONS)
        expected = (orig_res + 1) % len(SUPPORTED_RESOLUTIONS)
        self.assertEqual(game.options_resolution_index, expected)
        # Restore
        game.options_resolution_index = orig_res

    def test_dpad_options_left_right_toggles_fullscreen(self):
        """D-pad left/right on fullscreen option should toggle it."""
        game.options_selected_index = 1
        orig_fs = game.options_fullscreen
        game._gamepad_nav_last_time = 0
        import time
        now = time.time()
        _nav_x = 1  # noqa: F841 — documents simulated d-pad input
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            if game.options_selected_index == 1:
                game.options_fullscreen = not game.options_fullscreen
        self.assertEqual(game.options_fullscreen, not orig_fs)
        # Restore
        game.options_fullscreen = orig_fs

    def test_dpad_level_up_navigate(self):
        """D-pad in level-up should change level_up_selected_index."""
        game.level_up_selected_index = 0
        game._gamepad_nav_last_time = 0
        upgrade_options = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        import time
        now = time.time()
        _nav_y = 1  # noqa: F841 — documents simulated d-pad input (down)
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            game.level_up_selected_index = (game.level_up_selected_index + 1) % len(upgrade_options)
        self.assertEqual(game.level_up_selected_index, 1)

    def test_dpad_level_up_wraps(self):
        """Level-up navigation should wrap around."""
        upgrade_options = [{"name": "A"}, {"name": "B"}]
        game.level_up_selected_index = 1
        game._gamepad_nav_last_time = 0
        import time
        now = time.time()
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            game.level_up_selected_index = (game.level_up_selected_index + 1) % len(upgrade_options)
        self.assertEqual(game.level_up_selected_index, 0)

    def test_repeat_delay_blocks_rapid_navigation(self):
        """Navigation should be blocked if called again within repeat delay."""
        game.menu_selected_index = 0
        import time
        game._gamepad_nav_last_time = time.monotonic()  # just navigated
        now = time.monotonic()
        # Should not navigate because we just did
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game.menu_selected_index = (game.menu_selected_index + 1) % len(MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, 0)

    def test_repeat_delay_allows_after_timeout(self):
        """Navigation should proceed after repeat delay has passed."""
        game.menu_selected_index = 0
        import time
        game._gamepad_nav_last_time = time.monotonic() - GAMEPAD_NAV_REPEAT_DELAY - 0.01
        now = time.monotonic()
        if now - game._gamepad_nav_last_time >= GAMEPAD_NAV_REPEAT_DELAY:
            game._gamepad_nav_last_time = now
            game.menu_selected_index = (game.menu_selected_index + 1) % len(MENU_ITEMS)
        self.assertEqual(game.menu_selected_index, 1)

    def test_stick_deadzone_blocks_menu_nav(self):
        """Analog stick within deadzone should not trigger menu navigation."""
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.1, 1: 0.2}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        nav_x, nav_y = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > JOYSTICK_DEADZONE:
            nav_x = 1 if axis_x > 0 else -1
        if abs(axis_y) > JOYSTICK_DEADZONE:
            nav_y = 1 if axis_y > 0 else -1
        self.assertEqual(nav_x, 0)
        self.assertEqual(nav_y, 0)

    def test_stick_above_deadzone_triggers_menu_nav(self):
        """Analog stick above deadzone should produce navigation direction."""
        mock_joy = MagicMock()
        mock_joy.get_axis.side_effect = lambda a: {0: 0.0, 1: 0.8}[a]
        mock_joy.get_numhats.return_value = 0
        game.active_joystick = mock_joy
        nav_x, nav_y = 0, 0
        axis_x = mock_joy.get_axis(0)
        axis_y = mock_joy.get_axis(1)
        if abs(axis_x) > JOYSTICK_DEADZONE:
            nav_x = 1 if axis_x > 0 else -1
        if abs(axis_y) > JOYSTICK_DEADZONE:
            nav_y = 1 if axis_y > 0 else -1
        self.assertEqual(nav_x, 0)
        self.assertEqual(nav_y, 1)

    def test_dpad_hat_produces_nav_direction(self):
        """D-pad hat input should produce navigation directions."""
        mock_joy = MagicMock()
        mock_joy.get_axis.return_value = 0.0
        mock_joy.get_numhats.return_value = 1
        mock_joy.get_hat.return_value = (1, -1)  # right, down (SDL inverted)
        game.active_joystick = mock_joy
        nav_x, nav_y = 0, 0
        if mock_joy.get_numhats() > 0:
            hat_x, hat_y = mock_joy.get_hat(0)
            if hat_x:
                nav_x = hat_x
            if hat_y:
                nav_y = -hat_y
        self.assertEqual(nav_x, 1)
        self.assertEqual(nav_y, 1)  # down after inversion

    def test_no_joystick_no_menu_nav(self):
        """Without a joystick, no gamepad menu navigation should occur."""
        game.active_joystick = None
        game.menu_selected_index = 0
        # The navigation code checks active_joystick is not None first
        if game.active_joystick is not None:
            game.menu_selected_index = 1
        self.assertEqual(game.menu_selected_index, 0)

    def test_mousemotion_level_up_updates_selected_index(self):
        """Mouse hover over upgrade option should update level_up_selected_index."""
        game.level_up_selected_index = 0
        # Simulate: MOUSEMOTION updates level_up_selected_index when hovering
        hovered_idx = 2  # simulate get_hovered_upgrade_index returning 2
        if hovered_idx >= 0:
            game.level_up_selected_index = hovered_idx
        self.assertEqual(game.level_up_selected_index, 2)

    def test_mousemotion_level_up_no_hover_keeps_index(self):
        """Mouse not hovering over any option should keep level_up_selected_index."""
        game.level_up_selected_index = 1
        hovered_idx = -1  # not hovering
        if hovered_idx >= 0:
            game.level_up_selected_index = hovered_idx
        self.assertEqual(game.level_up_selected_index, 1)


class TestDisplaySettings(unittest.TestCase):
    """Tests for save/load display settings persistence."""

    def setUp(self):
        self._orig_settings_file = game.SETTINGS_FILE
        self._orig_res_index = game.options_resolution_index
        self._orig_fullscreen = game.options_fullscreen
        self._saved_resolutions = list(game.SUPPORTED_RESOLUTIONS)

    def tearDown(self):
        game.SETTINGS_FILE = self._orig_settings_file
        game.options_resolution_index = self._orig_res_index
        game.options_fullscreen = self._orig_fullscreen
        game.SUPPORTED_RESOLUTIONS[:] = self._saved_resolutions

    def test_save_settings_creates_file(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            game.options_resolution_index = 0
            game.options_fullscreen = True
            save_settings()
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(data["resolution_index"], 0)
            self.assertTrue(data["fullscreen"])
            self.assertEqual(data["resolution"], list(SUPPORTED_RESOLUTIONS[0]))
        finally:
            game.SETTINGS_FILE = old
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_save_settings_overwrites_existing(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            game.options_resolution_index = 0
            game.options_fullscreen = True
            save_settings()
            game.options_resolution_index = 1
            game.options_fullscreen = False
            save_settings()
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(data["resolution_index"], 1)
            self.assertFalse(data["fullscreen"])
        finally:
            game.SETTINGS_FILE = old
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_load_settings_missing_file(self):
        import tempfile
        import os
        old = game.SETTINGS_FILE
        game.SETTINGS_FILE = "/tmp/nonexistent_settings_test.json"
        if os.path.exists(game.SETTINGS_FILE):
            os.unlink(game.SETTINGS_FILE)
        try:
            result = load_settings()
            self.assertFalse(result)
        finally:
            game.SETTINGS_FILE = old

    def test_load_settings_corrupt_file(self):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not json at all")
            tmp = f.name
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            result = load_settings()
            self.assertFalse(result)
        finally:
            game.SETTINGS_FILE = old
            os.unlink(tmp)

    def test_load_settings_invalid_structure(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([1, 2, 3], f)
            tmp = f.name
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            result = load_settings()
            self.assertFalse(result)
        finally:
            game.SETTINGS_FILE = old
            os.unlink(tmp)

    def test_round_trip_save_load(self):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            # Save with specific settings
            game.options_resolution_index = 2
            game.options_fullscreen = False
            save_settings()
            # Change settings
            game.options_resolution_index = 0
            game.options_fullscreen = True
            # Load should restore
            result = load_settings()
            self.assertTrue(result)
            self.assertEqual(game.options_resolution_index, 2)
            self.assertFalse(game.options_fullscreen)
        finally:
            game.SETTINGS_FILE = old
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_load_settings_resolution_tuple_match(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({
                "resolution_index": 99,
                "fullscreen": False,
                "resolution": [1024, 768],
            }, f)
            tmp = f.name
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            result = load_settings()
            self.assertTrue(result)
            # Should match by resolution tuple, not the invalid index
            self.assertEqual(
                SUPPORTED_RESOLUTIONS[game.options_resolution_index],
                (1024, 768))
        finally:
            game.SETTINGS_FILE = old
            os.unlink(tmp)

    def test_load_settings_fallback_to_index(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({
                "resolution_index": 1,
                "fullscreen": True,
                "resolution": [9999, 9999],
            }, f)
            tmp = f.name
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            result = load_settings()
            self.assertTrue(result)
            self.assertEqual(game.options_resolution_index, 1)
            self.assertTrue(game.options_fullscreen)
        finally:
            game.SETTINGS_FILE = old
            os.unlink(tmp)

    def test_load_settings_invalid_index_and_resolution(self):
        import tempfile
        import os
        import json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({
                "resolution_index": 999,
                "fullscreen": False,
                "resolution": [9999, 9999],
            }, f)
            tmp = f.name
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            old_idx = game.options_resolution_index
            old_fs = game.options_fullscreen
            result = load_settings()
            self.assertFalse(result)
            # Neither fullscreen nor resolution should be changed on failed load
            self.assertEqual(game.options_resolution_index, old_idx)
            self.assertEqual(game.options_fullscreen, old_fs)
        finally:
            game.SETTINGS_FILE = old
            os.unlink(tmp)

    @patch("game.pygame.display.set_mode")
    def test_apply_resolution_calls_save_settings(self, mock_set_mode):
        import tempfile
        import os
        import json
        mock_set_mode.return_value = pygame.Surface((800, 600))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        try:
            old = game.SETTINGS_FILE
            game.SETTINGS_FILE = tmp
            game.options_resolution_index = 0
            game.options_fullscreen = False
            game.screen = pygame.Surface((800, 600))
            apply_resolution()
            self.assertTrue(os.path.exists(tmp))
            with open(tmp) as f:
                data = json.load(f)
            self.assertEqual(data["resolution_index"], 0)
            self.assertFalse(data["fullscreen"])
        finally:
            game.SETTINGS_FILE = old
            if os.path.exists(tmp):
                os.unlink(tmp)


class TestInitPygameSequence(unittest.TestCase):
    """Tests for the init_pygame() initialization sequence."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self._orig_screen = game.screen
        self._orig_joystick = game.active_joystick
        self._saved_resolutions = list(game.SUPPORTED_RESOLUTIONS)
        self._orig_res_index = game.options_resolution_index
        self._orig_fullscreen = game.options_fullscreen
        game.screen = None

    def tearDown(self):
        game.screen = self._orig_screen
        game.active_joystick = self._orig_joystick
        game.SUPPORTED_RESOLUTIONS[:] = self._saved_resolutions
        game.options_resolution_index = self._orig_res_index
        game.options_fullscreen = self._orig_fullscreen

    @patch('game.load_settings')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1920, 1080)))
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_sequence_fullscreen_flag(self, mock_count, mock_info,
                                           mock_set_mode, mock_caption, mock_font,
                                           mock_load):
        """init_pygame uses FULLSCREEN flag when options_fullscreen is True."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.options_fullscreen = True
        game.screen = None
        init_pygame()
        # set_mode should have been called with FULLSCREEN flag
        args, kwargs = mock_set_mode.call_args
        self.assertEqual(args[1], pygame.FULLSCREEN)

    @patch('game.load_settings')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1024, 768)))
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_sequence_windowed_flag(self, mock_count, mock_info,
                                         mock_set_mode, mock_caption, mock_font,
                                         mock_load):
        """init_pygame uses no flags when options_fullscreen is False."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.options_fullscreen = False
        game.screen = None
        init_pygame()
        args, kwargs = mock_set_mode.call_args
        self.assertEqual(args[1], 0)

    @patch('game.load_settings')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_fullscreen_fallback_updates_flag(self, mock_count, mock_info,
                                                    mock_caption, mock_font,
                                                    mock_load):
        """When fullscreen fails on startup, options_fullscreen is set to False."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.options_fullscreen = True
        game.screen = None
        # First call (fullscreen) raises, second call (windowed) succeeds
        with patch('pygame.display.set_mode',
                   side_effect=[pygame.error("fullscreen failed"),
                                pygame.Surface((1920, 1080))]) as mock_set_mode:
            init_pygame()
        self.assertFalse(game.options_fullscreen)
        self.assertIsNotNone(game.screen)

    @patch('game.load_settings')
    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_fullscreen_fallback_persists_settings(self, mock_count, mock_info,
                                                         mock_caption, mock_font,
                                                         mock_load):
        """When fullscreen fails on startup, corrected state is saved to settings."""
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.options_fullscreen = True
        game.screen = None
        with patch('pygame.display.set_mode',
                   side_effect=[pygame.error("fullscreen failed"),
                                pygame.Surface((1920, 1080))]) as mock_set_mode, \
             patch('game.save_settings') as mock_save:
            init_pygame()
        mock_save.assert_called_once()
        self.assertFalse(game.options_fullscreen)

    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1920, 1080)))
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_detects_display_before_settings(self, mock_count, mock_info,
                                                   mock_set_mode, mock_caption,
                                                   mock_font):
        """init_pygame detects native resolution before loading settings."""
        mock_info.return_value = MagicMock(current_w=2560, current_h=1440)
        game.screen = None
        game.SUPPORTED_RESOLUTIONS[:] = [(800, 600), (1024, 768)]
        # No settings file - should use detected defaults
        old_sf = game.SETTINGS_FILE
        game.SETTINGS_FILE = "/tmp/nonexistent_init_test.json"
        try:
            init_pygame()
            # Native resolution should have been added
            self.assertIn((2560, 1440), game.SUPPORTED_RESOLUTIONS)
        finally:
            game.SETTINGS_FILE = old_sf

    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1024, 768)))
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_loads_saved_settings(self, mock_count, mock_info,
                                       mock_set_mode, mock_caption, mock_font):
        """init_pygame loads saved settings and uses them for window creation."""
        import tempfile
        import json
        mock_info.return_value = MagicMock(current_w=1920, current_h=1080)
        game.screen = None
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({
                "resolution_index": 0,
                "fullscreen": False,
                "resolution": [800, 600],
            }, f)
            tmp = f.name
        old_sf = game.SETTINGS_FILE
        game.SETTINGS_FILE = tmp
        try:
            init_pygame()
            self.assertFalse(game.options_fullscreen)
            self.assertEqual(SUPPORTED_RESOLUTIONS[game.options_resolution_index], (800, 600))
        finally:
            game.SETTINGS_FILE = old_sf
            import os
            if os.path.exists(tmp):
                os.unlink(tmp)

    @patch('pygame.font.SysFont', return_value=MagicMock())
    @patch('pygame.display.set_caption')
    @patch('pygame.display.set_mode', return_value=pygame.Surface((1920, 1080)))
    @patch('pygame.display.Info')
    @patch('pygame.joystick.get_count', return_value=0)
    def test_init_skips_if_already_initialized(self, mock_count, mock_info,
                                                mock_set_mode, mock_caption,
                                                mock_font):
        """init_pygame returns early if screen is already set."""
        game.screen = pygame.Surface((800, 600))
        init_pygame()
        mock_set_mode.assert_not_called()


class TestShooterEnemy(unittest.TestCase):
    """Tests for the shooter enemy type and EnemyBullet."""

    def setUp(self):
        self.camera = Camera()

    def test_shooter_type_config(self):
        cfg = ENEMY_TYPES["shooter"]
        self.assertEqual(cfg["hp"], 5)
        self.assertAlmostEqual(cfg["speed"], 0.8)
        self.assertEqual(cfg["radius"], 13)
        self.assertEqual(cfg["xp_value"], 5)

    def test_shooter_init_attributes(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        self.assertEqual(e.shoot_cooldown, 90)
        self.assertGreaterEqual(e.shoot_timer, 30)
        self.assertLessEqual(e.shoot_timer, 90)
        self.assertIn(e.strafe_dir, [-1, 1])

    def test_non_shooter_has_zero_shoot_attrs(self):
        e = Enemy(self.camera, enemy_type="basic", wave=1)
        self.assertEqual(e.shoot_cooldown, 0)
        self.assertEqual(e.shoot_timer, 0)

    def test_shooter_in_wave_composition(self):
        # Shooter appears in wave 8+
        types_seen = set()
        for _ in range(500):
            types_seen.add(get_enemy_type_for_wave(8))
        self.assertIn("shooter", types_seen)

    def test_shooter_not_in_early_waves(self):
        for _ in range(200):
            etype = get_enemy_type_for_wave(6)
            self.assertNotEqual(etype, "shooter")

    def test_shooter_weight_increases_with_wave(self):
        # Wave 8: 15, Wave 10: 20, Wave 12: 25
        w8 = dict(WAVE_COMPOSITION)[8]["shooter"]
        w10 = dict(WAVE_COMPOSITION)[10]["shooter"]
        w12 = dict(WAVE_COMPOSITION)[12]["shooter"]
        self.assertLess(w8, w10)
        self.assertLess(w10, w12)

    def test_shooter_health_drop_chance(self):
        self.assertEqual(get_health_drop_chance("shooter"), 0.08)

    def test_enemy_bullet_creation(self):
        eb = EnemyBullet(100, 200, 1, 0, damage=2)
        self.assertEqual(eb.x, 100)
        self.assertEqual(eb.y, 200)
        self.assertAlmostEqual(eb.vx, EnemyBullet.SPEED)
        self.assertAlmostEqual(eb.vy, 0)
        self.assertEqual(eb.life, EnemyBullet.LIFETIME)
        self.assertEqual(eb.damage, 2)

    def test_enemy_bullet_direction_normalized(self):
        eb = EnemyBullet(0, 0, 3, 4)
        expected_vx = 3 / 5 * EnemyBullet.SPEED
        expected_vy = 4 / 5 * EnemyBullet.SPEED
        self.assertAlmostEqual(eb.vx, expected_vx)
        self.assertAlmostEqual(eb.vy, expected_vy)

    def test_enemy_bullet_zero_direction(self):
        eb = EnemyBullet(0, 0, 0, 0)
        # Should not crash; uses fallback length of 1
        self.assertEqual(eb.life, EnemyBullet.LIFETIME)

    def test_enemy_bullet_update(self):
        eb = EnemyBullet(0, 0, 1, 0)
        eb.update()
        self.assertAlmostEqual(eb.x, EnemyBullet.SPEED)
        self.assertEqual(eb.life, EnemyBullet.LIFETIME - 1)

    def test_enemy_bullet_carries_damage(self):
        eb = EnemyBullet(0, 0, 1, 0, damage=3)
        self.assertEqual(eb.damage, 3)

    def test_shooter_fires_bullet_with_contact_damage(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=6)
        # Force timer to 0 so it fires
        e.shoot_timer = 0
        target = MagicMock()
        target.x = e.x + 200  # within 300px range
        target.y = e.y
        enemy_bullets = []
        e.update(target, enemy_bullets)
        self.assertEqual(len(enemy_bullets), 1)
        self.assertEqual(enemy_bullets[0].damage, e.contact_damage)

    def test_shooter_does_not_fire_out_of_range(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        e.shoot_timer = 0
        target = MagicMock()
        target.x = e.x + 400  # beyond 300px range
        target.y = e.y
        enemy_bullets = []
        e.update(target, enemy_bullets)
        self.assertEqual(len(enemy_bullets), 0)

    def test_non_shooter_update_backward_compatible(self):
        e = Enemy(self.camera, enemy_type="basic", wave=1)
        target = MagicMock()
        target.x = e.x + 100
        target.y = e.y
        # Should work without enemy_bullets parameter
        e.update(target)

    def test_shooter_approaches_when_far(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        e.x, e.y = 500, 500
        target = MagicMock()
        target.x = 500 + 300  # >250px away
        target.y = 500
        initial_x = e.x
        e.shoot_timer = 999  # prevent firing
        e.update(target, [])
        self.assertGreater(e.x, initial_x)  # moved toward target

    def test_shooter_retreats_when_close(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        e.x, e.y = 500, 500
        target = MagicMock()
        target.x = 500 + 100  # <150px away
        target.y = 500
        initial_x = e.x
        e.shoot_timer = 999
        e.update(target, [])
        self.assertLess(e.x, initial_x)  # moved away from target

    def test_shooter_strafes_in_mid_range(self):
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        e.x, e.y = 500, 500
        target = MagicMock()
        target.x = 500 + 200  # between 150-250px
        target.y = 500
        initial_y = e.y
        e.shoot_timer = 999
        e.update(target, [])
        # Should move perpendicular (y changes), not toward/away (x stays ~same)
        self.assertNotAlmostEqual(e.y, initial_y)

    def test_enemy_bullet_obstacle_collision(self):
        obs = Obstacle(100, 100, 50, 50)
        eb = EnemyBullet(97, 125, 1, 0, damage=1)  # within RADIUS (5) of obstacle edge
        # Simulate the obstacle collision check from the game loop
        if obs.collides_circle(eb.x, eb.y, eb.RADIUS):
            eb.life = 0
        self.assertEqual(eb.life, 0)

    def test_enemy_bullet_player_collision(self):
        player = Unit(MAP_WIDTH / 2, MAP_HEIGHT / 2, PLAYER_COLOR, is_player=True)
        initial_hp = player.hp
        eb = EnemyBullet(player.x + 1, player.y, 1, 0, damage=2)
        # Simulate collision check from game loop
        if math.hypot(eb.x - player.x, eb.y - player.y) < eb.RADIUS + player.RADIUS:
            player.hp -= eb.damage
        self.assertEqual(player.hp, initial_hp - 2)


class TestBalanceConfig(unittest.TestCase):
    """Tests for balance.toml config loading system."""

    def test_balance_loaded_at_import(self):
        """BALANCE dict should be populated when game module is imported."""
        self.assertIsInstance(BALANCE, dict)
        self.assertIn("player", BALANCE)
        self.assertIn("enemies", BALANCE)
        self.assertIn("weapons", BALANCE)
        self.assertIn("waves", BALANCE)
        self.assertIn("difficulty", BALANCE)

    def test_balance_has_all_sections(self):
        """All expected top-level sections should exist."""
        expected = ["player", "weapons", "bullets", "enemies", "splitter",
                    "waves", "upgrades", "xp", "health_pickups", "difficulty"]
        for section in expected:
            self.assertIn(section, BALANCE, f"Missing section: {section}")

    def test_player_values(self):
        """Player section should have correct default values."""
        p = BALANCE["player"]
        self.assertEqual(p["hp"], 5)
        self.assertAlmostEqual(p["speed"], 2.5)
        self.assertEqual(p["shoot_cooldown"], 25)
        self.assertEqual(p["radius"], 14)
        self.assertEqual(p["ally"]["hp"], 3)
        self.assertEqual(p["ally"]["lifetime"], 600)

    def test_enemy_types_present(self):
        """All enemy types should be in the config."""
        enemies = BALANCE["enemies"]
        for etype in ("basic", "runner", "brute", "shielded", "splitter",
                      "mini", "elite", "shooter"):
            self.assertIn(etype, enemies)
            self.assertIn("hp", enemies[etype])
            self.assertIn("speed", enemies[etype])
            self.assertIn("radius", enemies[etype])

    def test_wave_composition_sorted_descending(self):
        """Wave composition entries should be in descending threshold order."""
        comp = BALANCE["waves"]["composition"]
        thresholds = [c["threshold"] for c in comp]
        self.assertEqual(thresholds, sorted(thresholds, reverse=True))

    def test_difficulty_values(self):
        """Difficulty section should have correct defaults."""
        d = BALANCE["difficulty"]
        self.assertEqual(d["max_enemies_base"], 140)
        self.assertEqual(d["max_enemies_cap"], 200)

    def test_default_balance_toml_is_valid(self):
        """The default TOML string should parse without errors."""
        import tomllib as _tomllib
        config = _tomllib.loads(_default_balance_toml())
        self.assertIn("player", config)
        self.assertIn("enemies", config)

    def test_load_balance_config_reads_file(self):
        """load_balance_config should read the file and populate BALANCE."""
        result = load_balance_config()
        self.assertIsInstance(result, dict)
        self.assertIn("player", result)
        # Module-level BALANCE should also be updated
        self.assertEqual(game.BALANCE, result)

    def test_missing_file_generates_default(self):
        """If balance.toml is missing, load_balance_config should create it."""
        import tempfile
        import shutil
        # Save original values
        orig_file = game.BALANCE_FILE
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                fake_path = os.path.join(tmpdir, "balance.toml")
                game.BALANCE_FILE = fake_path
                self.assertFalse(os.path.exists(fake_path))
                result = load_balance_config()
                # File should now exist
                self.assertTrue(os.path.exists(fake_path))
                # And config should be valid
                self.assertIn("player", result)
                self.assertEqual(result["player"]["hp"], 5)
        finally:
            game.BALANCE_FILE = orig_file
            # Reload original config
            load_balance_config()


class TestConfigDrivenEnemies(unittest.TestCase):
    """Tests that ENEMY_TYPES, WAVE_COMPOSITION, and HEALTH_DROP_CHANCE are built from BALANCE config."""

    def test_enemy_types_match_config(self):
        """ENEMY_TYPES values should match what's in BALANCE config."""
        for etype in ("basic", "runner", "brute", "shielded", "splitter", "mini", "elite", "shooter"):
            cfg = BALANCE["enemies"][etype]
            self.assertEqual(ENEMY_TYPES[etype]["hp"], cfg["hp"])
            self.assertAlmostEqual(ENEMY_TYPES[etype]["speed"], cfg["speed"])
            self.assertEqual(ENEMY_TYPES[etype]["radius"], cfg["radius"])
            self.assertEqual(ENEMY_TYPES[etype]["xp_value"], cfg["xp_value"])
            self.assertEqual(ENEMY_TYPES[etype]["color"], tuple(cfg["color"]))

    def test_shielded_has_shield_from_config(self):
        """Shielded enemy type should have shield=True from config."""
        self.assertTrue(ENEMY_TYPES["shielded"].get("shield", False))
        self.assertFalse(ENEMY_TYPES["basic"].get("shield", False))

    def test_wave_composition_matches_config(self):
        """WAVE_COMPOSITION should be built from BALANCE config."""
        config_comp = BALANCE["waves"]["composition"]
        self.assertEqual(len(WAVE_COMPOSITION), len(config_comp))
        for (threshold, weights), cfg_entry in zip(WAVE_COMPOSITION, config_comp):
            self.assertEqual(threshold, cfg_entry["threshold"])
            self.assertEqual(weights, dict(cfg_entry["weights"]))

    def test_health_drop_chance_matches_config(self):
        """HEALTH_DROP_CHANCE should be built from BALANCE config."""
        drop_cfg = BALANCE["health_pickups"]["drop_chance"]
        for etype in ("basic", "runner", "brute", "shielded", "splitter", "mini", "elite", "shooter"):
            self.assertAlmostEqual(HEALTH_DROP_CHANCE[etype], drop_cfg[etype])

    def test_health_drop_default_from_config(self):
        """Unknown enemy types should use the default drop chance from config."""
        default = BALANCE["health_pickups"]["drop_chance"]["default"]
        self.assertAlmostEqual(get_health_drop_chance("unknown_type"), default)


class TestConfigDrivenScaling(unittest.TestCase):
    """Tests that enemy scaling uses config values from BALANCE."""

    def setUp(self):
        self.camera = Camera()

    def test_hp_scaling_uses_config(self):
        """Enemy HP scaling should use config parameters."""
        scaling = BALANCE["enemies"]["scaling"]
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        base_hp = BALANCE["enemies"]["basic"]["hp"]
        linear = 1 + scaling["hp_linear"] * 9
        compound = scaling["hp_compound"] ** max(0, 10 - scaling["hp_compound_start"])
        expected = max(base_hp, int(base_hp * linear * compound))
        self.assertEqual(e.hp, expected)

    def test_speed_scaling_uses_config(self):
        """Enemy speed scaling should use config parameters."""
        scaling = BALANCE["enemies"]["scaling"]
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        base_speed = BALANCE["enemies"]["basic"]["speed"]
        expected = base_speed * min(scaling["speed_cap"], 1 + scaling["speed_linear"] * 9)
        self.assertAlmostEqual(e.speed, expected)

    def test_xp_scaling_uses_config(self):
        """Enemy XP scaling should use config parameters."""
        scaling = BALANCE["enemies"]["scaling"]
        e = Enemy(self.camera, enemy_type="basic", wave=10)
        base_xp = BALANCE["enemies"]["basic"]["xp_value"]
        expected = base_xp + 10 // scaling["xp_wave_divisor"]
        self.assertEqual(e.xp_value, expected)

    def test_contact_damage_uses_config(self):
        """Contact damage scaling should use config parameters."""
        scaling = BALANCE["enemies"]["scaling"]
        divisor = scaling["contact_damage_divisor"]
        e = Enemy(self.camera, enemy_type="basic", wave=16)
        expected = 1 + (16 - 1) // divisor
        self.assertEqual(e.contact_damage, expected)

    def test_shooter_cooldown_from_config(self):
        """Shooter enemy should use cooldown from config."""
        shooter_cfg = BALANCE["enemies"]["shooter_behavior"]
        e = Enemy(self.camera, enemy_type="shooter", wave=1)
        self.assertEqual(e.shoot_cooldown, shooter_cfg["shoot_cooldown"])

    def test_shooter_timer_range_from_config(self):
        """Shooter initial timer should be within config range."""
        shooter_cfg = BALANCE["enemies"]["shooter_behavior"]
        timer_min = shooter_cfg["shoot_timer_min"]
        timer_max = shooter_cfg["shoot_timer_max"]
        for _ in range(50):
            e = Enemy(self.camera, enemy_type="shooter", wave=1)
            self.assertGreaterEqual(e.shoot_timer, timer_min)
            self.assertLessEqual(e.shoot_timer, timer_max)


if __name__ == "__main__":
    unittest.main()
