"""Pixel-level display checks; no camera, model or FPGA is needed."""

from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fpga.demo.pose_overlay import draw_static_pose


GREEN = np.array([80, 220, 80], dtype=np.uint8)


def body_points():
    points = np.zeros((17, 3), dtype=np.float32)
    points[5:15] = [(150, 80, 1), (350, 80, 1), (120, 160, 1),
                    (380, 160, 1), (80, 220, 1), (420, 220, 1),
                    (180, 270, 1), (320, 270, 1), (160, 410, 1),
                    (340, 410, 1)]
    return points


class StaticPoseOverlayTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((500, 500, 3), dtype=np.uint8)

    def assert_green_near(self, image, xy):
        x, y = np.rint(xy).astype(int)
        patch = image[y-2:y+3, x-2:x+3]
        self.assertTrue(np.all(patch == GREEN, axis=2).any(), (x, y))

    def test_draws_every_body_bone_and_joint_in_green(self):
        points = body_points()
        image = draw_static_pose(self.frame, points)
        for start, end in [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
                           (5, 11), (6, 12), (11, 12), (11, 13), (12, 14)]:
            self.assert_green_near(image, (points[start, :2] + points[end, :2]) / 2)
        for point in points[5:15, :2]:
            self.assert_green_near(image, point)

    def test_mask_hides_joint_and_its_connections_but_keeps_partial_body(self):
        points = body_points()
        mask = np.ones(10, dtype=bool)
        mask[0] = False
        image = draw_static_pose(self.frame, points, mask)
        for x, y in [(150, 80), (250, 80), (135, 120), (165, 175)]:
            self.assertFalse(image[y-3:y+4, x-3:x+4].any(), (x, y))
        self.assert_green_near(image, points[7, :2])
        self.assert_green_near(image, (points[7, :2] + points[9, :2]) / 2)

    def test_none_and_unusable_body_return_independent_unchanged_copies(self):
        for points in [None, np.zeros((17, 3)), np.full((17, 3), np.nan),
                       np.full((17, 3), np.inf)]:
            with self.subTest(points=points is None):
                image = draw_static_pose(self.frame, points)
                np.testing.assert_array_equal(image, self.frame)
                self.assertFalse(np.shares_memory(image, self.frame))

    def test_mask_cannot_override_confidence_finiteness_or_frame_margin(self):
        points = np.zeros((17, 3), dtype=np.float64)
        points[5:15] = [(10, 100, 1), (490, 100, 1), (100, 10, 1),
                        (100, 490, 1), (100, 100, .249), (np.nan, 100, 1),
                        (100, np.inf, 1), (100, 100, np.nan),
                        (-1e200, 100, 1), (1e200, 100, 1)]
        image = draw_static_pose(self.frame, points, np.ones(10, dtype=bool))
        self.assertFalse(image.any())

    def test_thresholds_include_exact_margin_and_confidence(self):
        points = np.zeros((17, 3), dtype=np.float32)
        points[5], points[6] = (20, 20, .25), (480, 20, .25)
        image = draw_static_pose(self.frame, points)
        self.assert_green_near(image, (250, 20))
        self.assert_green_near(image, (20, 20))
        self.assert_green_near(image, (480, 20))

    def test_head_and_feet_are_never_drawn(self):
        points = np.zeros((17, 3), dtype=np.float32)
        points[:5] = (250, 50, 1)
        points[15:] = (250, 450, 1)
        self.assertFalse(draw_static_pose(self.frame, points).any())

    def test_inputs_are_not_modified(self):
        points = body_points()
        mask = np.ones(10, dtype=bool)
        original_points, original_mask = points.copy(), mask.copy()
        draw_static_pose(self.frame, points, mask)
        self.assertFalse(self.frame.any())
        np.testing.assert_array_equal(points, original_points)
        np.testing.assert_array_equal(mask, original_mask)

    def test_rejects_incompatible_shapes(self):
        with self.assertRaises(ValueError):
            draw_static_pose(self.frame, np.zeros((10, 3)))
        with self.assertRaises(ValueError):
            draw_static_pose(self.frame, body_points(), np.ones(17))


if __name__ == '__main__':
    unittest.main()
