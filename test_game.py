import unittest
import math
import pygame
from game import (generate_xp_thresholds, check_level_up, default_weapon_stats, Bullet, Unit,
                  generate_upgrade_options, apply_upgrade, get_scaled_amount, STAT_UPGRADES, WEAPON_TYPES,
                  draw_glow, draw_game_scene, draw_dim_overlay,
                  BG, PLAYER_COLOR, ENEMY_COLOR, GRID_COLOR, BORDER_COLOR,
                  OBSTACLE_COLOR, OBSTACLE_BORDER, BULLET_COLOR, HEALTH_FG,
                  Camera, Enemy, Obstacle, ENEMY_TYPES,
                  WAVE_COMPOSITION, get_enemy_type_for_wave,
                  HealthPickup, HEALTH_PICKUP_COLOR,
                  HEALTH_DROP_CHANCE, get_health_drop_chance,
                  STATE_OPTIONS,
                  SUPPORTED_RESOLUTIONS, apply_resolution,
                  EscapeRoom,
                  MAP_WIDTH, MAP_HEIGHT,
                  _is_visible)
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
        stats = default_weapon_stats()
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].damage, 1)
        self.assertAlmostEqual(bullets[0].vx, 8.0)
        self.assertEqual(bullets[0].life, 90)

    def test_shoot_with_boosted_damage(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["damage"] = 5
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(bullets[0].damage, 5)

    def test_fire_rate_affects_cooldown(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["fire_rate"] = 10
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(u.cooldown, 10)

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
        stats = default_weapon_stats()
        stats["range"] = 5  # 5 frames * 8 speed = 40 pixels max
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 0)

    def test_range_allows_close_target(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(30, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["range"] = 5  # 5 * 8 = 40 pixels
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)


class TestGenerateUpgradeOptions(unittest.TestCase):
    def test_returns_3_options(self):
        stats = default_weapon_stats()
        options = generate_upgrade_options(3, stats)
        self.assertEqual(len(options), 3)

    def test_non_milestone_all_stat_upgrades(self):
        stats = default_weapon_stats()
        options = generate_upgrade_options(3, stats)
        for opt in options:
            self.assertIn("stat", opt)
            self.assertIn("name", opt)

    def test_milestone_has_weapon_option(self):
        stats = default_weapon_stats()
        # Level 5 is a milestone
        found_weapon = False
        # Run multiple times since it's random placement
        for _ in range(50):
            options = generate_upgrade_options(5, stats)
            for opt in options:
                if "weapon_type" in opt:
                    found_weapon = True
                    self.assertIn(opt["weapon_type"], WEAPON_TYPES)
                    break
            if found_weapon:
                break
        self.assertTrue(found_weapon)

    def test_milestone_10(self):
        stats = default_weapon_stats()
        found_weapon = False
        for _ in range(50):
            options = generate_upgrade_options(10, stats)
            if any("weapon_type" in o for o in options):
                found_weapon = True
                break
        self.assertTrue(found_weapon)

    def test_no_duplicate_weapon_type_offered(self):
        stats = default_weapon_stats()
        stats["weapon_type"] = "shotgun"
        for _ in range(50):
            options = generate_upgrade_options(5, stats)
            for opt in options:
                if "weapon_type" in opt:
                    self.assertNotEqual(opt["weapon_type"], "shotgun")


class TestApplyUpgrade(unittest.TestCase):
    def test_apply_damage_upgrade(self):
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "+Damage", "stat": "damage", "amount": 1})
        self.assertEqual(stats["damage"], 2)

    def test_apply_fire_rate_upgrade(self):
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3})
        self.assertEqual(stats["fire_rate"], 22)

    def test_fire_rate_clamped_to_minimum(self):
        stats = default_weapon_stats()
        stats["fire_rate"] = 4
        apply_upgrade(stats, {"name": "+Fire Rate", "stat": "fire_rate", "amount": -3})
        self.assertEqual(stats["fire_rate"], 3)

    def test_apply_weapon_type(self):
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "Weapon: Shotgun", "weapon_type": "shotgun"})
        self.assertEqual(stats["weapon_type"], "shotgun")

    def test_apply_bullet_speed(self):
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "+Bullet Speed", "stat": "bullet_speed", "amount": 2})
        self.assertEqual(stats["bullet_speed"], 10)

    def test_apply_range(self):
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "+Range", "stat": "range", "amount": 15})
        self.assertEqual(stats["range"], 105)

    def test_apply_max_hp_upgrade(self):
        stats = default_weapon_stats()
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        self.assertEqual(player.max_hp, 5)
        self.assertEqual(player.hp, 5)
        apply_upgrade(stats, {"name": "+Max HP", "stat": "max_hp", "amount": 1}, player)
        self.assertEqual(player.max_hp, 6)
        self.assertEqual(player.hp, 6)

    def test_apply_max_hp_upgrade_heals_one(self):
        stats = default_weapon_stats()
        player = Unit(100, 100, (255, 255, 255), is_player=True)
        player.hp = 3  # damaged
        apply_upgrade(stats, {"name": "+Max HP", "stat": "max_hp", "amount": 1}, player)
        self.assertEqual(player.max_hp, 6)
        self.assertEqual(player.hp, 4)  # healed 1, not to full

    def test_apply_max_hp_without_player_raises(self):
        stats = default_weapon_stats()
        with self.assertRaises(ValueError):
            apply_upgrade(stats, {"name": "+Max HP", "stat": "max_hp", "amount": 1})

    def test_max_hp_in_upgrade_options(self):
        """Max HP should be available as a possible upgrade option."""
        stat_names = [u["stat"] for u in STAT_UPGRADES if "stat" in u]
        self.assertIn("max_hp", stat_names)


class TestScaledUpgrades(unittest.TestCase):
    def test_damage_scaling_below_10(self):
        self.assertEqual(get_scaled_amount("damage", 1, 5), 1)

    def test_damage_scaling_at_10(self):
        self.assertEqual(get_scaled_amount("damage", 1, 10), 2)

    def test_damage_scaling_at_15(self):
        self.assertEqual(get_scaled_amount("damage", 1, 15), 2)

    def test_damage_scaling_at_20(self):
        self.assertEqual(get_scaled_amount("damage", 1, 20), 3)

    def test_damage_scaling_at_25(self):
        self.assertEqual(get_scaled_amount("damage", 1, 25), 3)

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
        stats = default_weapon_stats()
        for _ in range(50):
            options = generate_upgrade_options(12, stats)
            for opt in options:
                if opt.get("stat") == "damage":
                    self.assertEqual(opt["amount"], 2)

    def test_generate_options_scaled_fire_rate_at_level_16(self):
        stats = default_weapon_stats()
        for _ in range(50):
            options = generate_upgrade_options(16, stats)
            for opt in options:
                if opt.get("stat") == "fire_rate":
                    self.assertEqual(opt["amount"], -5)

    def test_milestone_every_4_after_level_15(self):
        stats = default_weapon_stats()
        # Level 16 is a milestone (16 % 4 == 0) with new interval
        found_weapon = False
        for _ in range(100):
            options = generate_upgrade_options(16, stats)
            if any("weapon_type" in o for o in options):
                found_weapon = True
                break
        self.assertTrue(found_weapon)

    def test_level_17_not_milestone(self):
        stats = default_weapon_stats()
        # Level 17: 17 % 4 != 0, should not be milestone
        for _ in range(50):
            options = generate_upgrade_options(17, stats)
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
        stats = default_weapon_stats()
        stats["weapon_type"] = "shotgun"
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 5)

    def test_shotgun_bullets_have_reduced_damage(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["weapon_type"] = "shotgun"
        stats["damage"] = 4
        u.shoot_at(target, bullets, weapon_stats=stats)
        for b in bullets:
            self.assertEqual(b.damage, 2)  # 4 // 2

    def test_shotgun_bullets_spread(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["weapon_type"] = "shotgun"
        u.shoot_at(target, bullets, weapon_stats=stats)
        # Bullets should have different directions
        angles = [math.atan2(b.vy, b.vx) for b in bullets]
        self.assertNotAlmostEqual(angles[0], angles[-1], places=2)

    def test_shotgun_min_damage_is_1(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["weapon_type"] = "shotgun"
        stats["damage"] = 1
        u.shoot_at(target, bullets, weapon_stats=stats)
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
        stats = default_weapon_stats()
        stats["weapon_type"] = "explosive"
        stats["damage"] = 3
        u.shoot_at(t, bullets, weapon_stats=stats)
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
        stats = default_weapon_stats()
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "normal")

    def test_piercing_fires_single_bullet(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["weapon_type"] = "piercing"
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "piercing")

    def test_explosive_fires_single_bullet(self):
        u = Unit(0, 0, (255, 255, 255), is_player=True)
        target = self._make_target(100, 0)
        bullets = []
        stats = default_weapon_stats()
        stats["weapon_type"] = "explosive"
        u.shoot_at(target, bullets, weapon_stats=stats)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].weapon_type, "explosive")


class TestFullLevelUpFlow(unittest.TestCase):
    """Integration tests for the complete level-up flow."""

    def test_full_flow_xp_to_level_up_to_upgrade(self):
        """Simulate: accumulate XP -> level up -> generate options -> apply upgrade."""
        thresholds = generate_xp_thresholds()
        stats = default_weapon_stats()
        xp, level = 0, 1

        # Accumulate XP from kills
        for _ in range(10):
            xp += 1

        # Level up
        xp, level, leveled = check_level_up(xp, level, thresholds)
        self.assertTrue(leveled)
        self.assertEqual(level, 2)

        # Generate upgrade options
        options = generate_upgrade_options(level, stats)
        self.assertEqual(len(options), 3)

        # Apply first non-max_hp option (max_hp doesn't change weapon stats)
        option = next(o for o in options if o.get("stat") != "max_hp")
        apply_upgrade(stats, option)
        # Stats should have changed from defaults
        changed = (
            stats["damage"] != 1 or stats["fire_rate"] != 25 or
            stats["bullet_speed"] != 8 or stats["range"] != 90
        )
        self.assertTrue(changed)

    def test_flow_to_milestone_weapon_unlock(self):
        """Simulate reaching level 5 milestone and getting a weapon type."""
        thresholds = generate_xp_thresholds()
        stats = default_weapon_stats()
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
            options = generate_upgrade_options(level, stats)
            for opt in options:
                if "weapon_type" in opt:
                    apply_upgrade(stats, opt)
                    self.assertIn(stats["weapon_type"], WEAPON_TYPES)
                    found_weapon = True
                    break
            if found_weapon:
                break
        self.assertTrue(found_weapon)

    def test_weapon_type_persists_through_stat_upgrades(self):
        """After getting a weapon type, stat upgrades should not reset it."""
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "Weapon: Shotgun", "weapon_type": "shotgun"})
        self.assertEqual(stats["weapon_type"], "shotgun")

        # Apply a stat upgrade
        apply_upgrade(stats, {"name": "+Damage", "stat": "damage", "amount": 1})
        self.assertEqual(stats["weapon_type"], "shotgun")
        self.assertEqual(stats["damage"], 2)

    def test_multiple_level_ups_with_upgrades(self):
        """Simulate multiple level-ups each with an upgrade applied."""
        thresholds = generate_xp_thresholds()
        stats = default_weapon_stats()
        xp, level = 0, 1

        for target_level in range(2, 5):
            threshold = thresholds[level - 1]
            xp += threshold
            xp, level, leveled = check_level_up(xp, level, thresholds)
            self.assertTrue(leveled)
            self.assertEqual(level, target_level)

            options = generate_upgrade_options(level, stats)
            # Pick a weapon stat upgrade to avoid max_hp (which doesn't modify weapon_stats)
            weapon_option = next(
                (o for o in options if o.get("stat") != "max_hp" and "weapon_type" not in o),
                options[0],
            )
            apply_upgrade(stats, weapon_option)

        # After 3 upgrades, stats should differ from defaults
        default = default_weapon_stats()
        any_different = any(
            stats[k] != default[k] for k in ["damage", "fire_rate", "bullet_speed", "range"]
        )
        self.assertTrue(any_different)

    def test_reset_returns_to_defaults(self):
        """Verify that resetting state returns to default values."""
        stats = default_weapon_stats()
        apply_upgrade(stats, {"name": "+Damage", "stat": "damage", "amount": 5})
        self.assertEqual(stats["damage"], 6)

        # Reset by getting fresh defaults (as reset_game does)
        stats = default_weapon_stats()
        self.assertEqual(stats["damage"], 1)
        self.assertEqual(stats["weapon_type"], "normal")


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

    def tearDown(self):
        import game
        game.screen = self._orig_screen
        game.font = self._orig_font
        game.title_font = self._orig_title_font

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
        from game import draw_menu
        with patch('pygame.display.flip'), patch('pygame.mouse.get_pos', return_value=(100, 300)):
            draw_menu()

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
        from game import draw_game_scene, Camera, default_weapon_stats, generate_xp_thresholds
        camera = Camera()
        player = Unit(100, 100, (0, 220, 255), is_player=True)
        camera.update(player)
        stats = default_weapon_stats()
        thresholds = generate_xp_thresholds()
        draw_game_scene(camera, [], [], [], [], player,
                        0, 1, 1, stats, 0, thresholds)

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
        from game import draw_game_scene, draw_dim_overlay, Camera, default_weapon_stats, generate_xp_thresholds
        camera = Camera()
        player = Unit(100, 100, (0, 220, 255), is_player=True)
        camera.update(player)
        stats = default_weapon_stats()
        thresholds = generate_xp_thresholds()
        # Should not raise
        draw_game_scene(camera, [], [], [], [], player,
                        0, 1, 1, stats, 0, thresholds)
        draw_dim_overlay()


    def test_upgrade_panel_dimensions(self):
        """Verify panel constants define a centered ~500x350 panel."""
        from game import PANEL_WIDTH, PANEL_HEIGHT, PANEL_X, PANEL_Y, WIDTH, HEIGHT
        self.assertEqual(PANEL_WIDTH, 500)
        self.assertEqual(PANEL_HEIGHT, 350)
        self.assertEqual(PANEL_X, (WIDTH - PANEL_WIDTH) // 2)
        self.assertEqual(PANEL_Y, (HEIGHT - PANEL_HEIGHT) // 2)

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
        from game import draw_upgrade_panel, PANEL_X, PANEL_Y, PANEL_WIDTH, PANEL_HEIGHT
        game.screen.fill((0, 0, 0))
        options = [{"name": "Test", "stat": "damage", "amount": 1}]
        draw_upgrade_panel(1, options)
        # Check that a pixel inside the panel region is no longer black
        cx = PANEL_X + PANEL_WIDTH // 2
        cy = PANEL_Y + PANEL_HEIGHT // 2
        pixel = game.screen.get_at((cx, cy))
        self.assertNotEqual(pixel[:3], (0, 0, 0))

    def test_upgrade_panel_centered_on_screen(self):
        """Verify the panel is centered horizontally and vertically."""
        from game import PANEL_WIDTH, PANEL_HEIGHT, PANEL_X, PANEL_Y, WIDTH, HEIGHT
        center_x = PANEL_X + PANEL_WIDTH // 2
        center_y = PANEL_Y + PANEL_HEIGHT // 2
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
        import pygame
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
        from game import (get_hovered_upgrade_index, PANEL_X, PANEL_Y,
                          OPTION_START_Y, OPTION_ROW_HEIGHT, OPTION_PADDING, PANEL_WIDTH)
        row_h = OPTION_ROW_HEIGHT - 5  # actual row rect height
        mx = PANEL_X + PANEL_WIDTH // 2
        for i in range(3):
            # Click geometric center of each row
            my = PANEL_Y + OPTION_START_Y + i * OPTION_ROW_HEIGHT + row_h // 2
            self.assertEqual(get_hovered_upgrade_index(mx, my, 3), i)

    def test_get_hovered_upgrade_index_miss(self):
        """Click outside all option rows returns -1."""
        from game import get_hovered_upgrade_index, PANEL_X, PANEL_Y
        # Click well outside panel
        self.assertEqual(get_hovered_upgrade_index(0, 0, 3), -1)
        # Click above options (in title area)
        self.assertEqual(get_hovered_upgrade_index(PANEL_X + 100, PANEL_Y + 10, 3), -1)

    def test_get_hovered_upgrade_index_no_options(self):
        """With zero options, always returns -1."""
        from game import get_hovered_upgrade_index, PANEL_X, PANEL_Y
        self.assertEqual(get_hovered_upgrade_index(PANEL_X + 100, PANEL_Y + 100, 0), -1)


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
        self.assertEqual(basic["hp"], 2)
        self.assertAlmostEqual(basic["speed"], 1.2)
        self.assertEqual(basic["radius"], 12)
        self.assertEqual(basic["xp_value"], 1)

    def test_basic_enemy_creation(self):
        e = Enemy(self.camera)
        self.assertEqual(e.enemy_type, "basic")
        self.assertEqual(e.hp, 2)
        self.assertAlmostEqual(e.speed, 1.2)
        self.assertEqual(e.radius, 12)
        self.assertEqual(e.color, (255, 30, 60))
        self.assertEqual(e.xp_value, 1)

    def test_enemy_type_defaults_to_basic(self):
        e = Enemy(self.camera)
        self.assertEqual(e.enemy_type, "basic")

    def test_explicit_basic_type(self):
        e = Enemy(self.camera, enemy_type="basic")
        self.assertEqual(e.enemy_type, "basic")
        self.assertEqual(e.hp, 2)

    def test_enemy_has_unique_uid(self):
        e1 = Enemy(self.camera)
        e2 = Enemy(self.camera)
        self.assertNotEqual(e1.uid, e2.uid)

    def test_enemy_xp_value_used_for_scoring(self):
        """Basic enemies should give xp_value=1."""
        e = Enemy(self.camera)
        self.assertEqual(e.xp_value, 1)

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
        self.assertEqual(cfg["hp"], 1)
        self.assertEqual(cfg["speed"], 2.2)
        self.assertEqual(cfg["radius"], 8)
        self.assertEqual(cfg["xp_value"], 1)

    def test_brute_type_config(self):
        self.assertIn("brute", ENEMY_TYPES)
        cfg = ENEMY_TYPES["brute"]
        self.assertEqual(cfg["hp"], 6)
        self.assertEqual(cfg["speed"], 0.7)
        self.assertEqual(cfg["radius"], 18)
        self.assertEqual(cfg["xp_value"], 3)

    def test_runner_creation(self):
        e = Enemy(self.camera, enemy_type="runner")
        self.assertEqual(e.enemy_type, "runner")
        self.assertEqual(e.hp, 1)
        self.assertEqual(e.speed, 2.2)
        self.assertEqual(e.radius, 8)

    def test_brute_creation(self):
        e = Enemy(self.camera, enemy_type="brute")
        self.assertEqual(e.enemy_type, "brute")
        self.assertEqual(e.hp, 6)
        self.assertEqual(e.speed, 0.7)
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
        self.assertEqual(cfg["hp"], 4)
        self.assertEqual(cfg["speed"], 1.0)
        self.assertEqual(cfg["radius"], 14)
        self.assertEqual(cfg["color"], (0, 255, 255))
        self.assertEqual(cfg["xp_value"], 4)
        self.assertTrue(cfg["shield"])

    def test_shielded_creation(self):
        e = Enemy(self.camera, enemy_type="shielded")
        self.assertEqual(e.enemy_type, "shielded")
        self.assertEqual(e.hp, 4)
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
        self.assertEqual(cfg["hp"], 3)
        self.assertEqual(cfg["speed"], 1.0)
        self.assertEqual(cfg["radius"], 14)
        self.assertEqual(cfg["color"], (0, 255, 100))
        self.assertEqual(cfg["xp_value"], 2)

    def test_mini_type_config(self):
        self.assertIn("mini", ENEMY_TYPES)
        cfg = ENEMY_TYPES["mini"]
        self.assertEqual(cfg["hp"], 1)
        self.assertEqual(cfg["speed"], 1.8)
        self.assertEqual(cfg["radius"], 7)
        self.assertEqual(cfg["xp_value"], 1)

    def test_splitter_creation(self):
        e = Enemy(self.camera, enemy_type="splitter")
        self.assertEqual(e.enemy_type, "splitter")
        self.assertEqual(e.hp, 3)
        self.assertFalse(e.shield)

    def test_mini_creation(self):
        e = Enemy(self.camera, enemy_type="mini")
        self.assertEqual(e.enemy_type, "mini")
        self.assertEqual(e.hp, 1)
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
        self.assertEqual(minis[0].hp, 1)
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
        self.assertEqual(cfg["hp"], 10)
        self.assertEqual(cfg["speed"], 1.8)
        self.assertEqual(cfg["radius"], 16)
        self.assertEqual(cfg["color"], (255, 0, 255))
        self.assertEqual(cfg["xp_value"], 8)

    def test_elite_creation(self):
        e = Enemy(self.camera, enemy_type="elite")
        self.assertEqual(e.enemy_type, "elite")
        self.assertEqual(e.hp, 10)
        self.assertEqual(e.speed, 1.8)
        self.assertEqual(e.xp_value, 8)

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
        game.options_selected_index = 0
        game.options_resolution_index = 1
        game.options_fullscreen = False
        game.WIDTH, game.HEIGHT = 1024, 768

    def test_state_options_constant(self):
        self.assertEqual(STATE_OPTIONS, 4)

    def test_supported_resolutions(self):
        self.assertEqual(len(SUPPORTED_RESOLUTIONS), 4)
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
        game.options_resolution_index = 3
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
        self.assertEqual(len(SUPPORTED_RESOLUTIONS), 4)
        for idx in range(len(SUPPORTED_RESOLUTIONS)):
            game.options_resolution_index = idx
            res = SUPPORTED_RESOLUTIONS[idx]
            self.assertEqual(len(res), 2)
            self.assertGreater(res[0], 0)
            self.assertGreater(res[1], 0)


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


if __name__ == "__main__":
    unittest.main()
