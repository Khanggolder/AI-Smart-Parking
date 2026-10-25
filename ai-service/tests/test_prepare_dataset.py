"""Small W1 unit tests. Run: python -m unittest discover -s ai-service/tests -v"""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_dataset import make_crop, split_days  # noqa: E402


class PreparationTests(unittest.TestCase):
    def test_crop_shape_and_polygon_mask(self):
        image = np.full((80, 120, 3), 255, np.uint8)
        polygon = np.array([[20, 10], [70, 15], [60, 65], [15, 58]], np.int32)
        crop = make_crop(image, [polygon], size=224, mode="mask")
        self.assertEqual(crop.shape, (224, 224, 3))
        self.assertTrue(np.any(crop == 114))
        self.assertTrue(np.any(crop == 255))

    def test_no_shared_days(self):
        dates = [f"2026-09-{day:02d}" for day in range(1, 13)]
        splits = split_days(dates, seed=42)
        self.assertEqual(set.union(*splits.values()), set(dates))
        for a in splits:
            for b in splits:
                if a != b:
                    self.assertFalse(splits[a] & splits[b])


if __name__ == "__main__":
    unittest.main()
