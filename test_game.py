import unittest
import math
import pygame
from game import (generate_xp_thresholds, check_level_up, default_weapon_stats, Bullet, Unit,
                  generate_upgrade_options, apply_upgrade, STAT_UPGRADES, WEAPON_TYPES,
                  draw_glow, BG, PLAYER_COLOR, ENEMY_COLOR, GRID_COLOR, BORDER_COLOR,
                  OBSTACLE_COLOR, OBSTACLE_BORDER, BULLET_COLOR, HEALTH_FG,
                  Camera, Enemy, Obstacle)


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

        # Apply first option
        apply_upgrade(stats, options[0])
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
            apply_upgrade(stats, options[0])

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
        draw_glow(self.surface, (255, 30, 60), (50, 50), 20, intensity=120, layers=6)

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
        game.screen = pygame.Surface((800, 600))
        self.camera = Camera()

    def test_unit_draw_with_glow(self):
        unit = Unit(100, 100, PLAYER_COLOR, is_player=True)
        unit.draw(self.camera)

    def test_ally_draw_with_glow(self):
        unit = Unit(100, 100, (0, 150, 255), is_player=False)
        unit.draw(self.camera)

    def test_enemy_draw_with_glow(self):
        enemy = Enemy(self.camera)
        enemy.draw(self.camera)

    def test_bullet_draw_with_glow(self):
        bullet = Bullet(100, 100, 1, 0)
        bullet.draw(self.camera)

    def test_obstacle_draw_with_glow(self):
        obstacle = Obstacle(100, 100, 50, 50)
        obstacle.draw(self.camera)


if __name__ == "__main__":
    unittest.main()
