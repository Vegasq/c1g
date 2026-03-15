import unittest
import math
from game import generate_xp_thresholds, check_level_up, default_weapon_stats, Bullet, Unit


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


if __name__ == "__main__":
    unittest.main()
