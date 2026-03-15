import unittest
from game import generate_xp_thresholds, check_level_up


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


if __name__ == "__main__":
    unittest.main()
