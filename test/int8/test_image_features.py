"""Real spatial image math and metadata contracts, using synthetic pixels only."""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.image_features import (CONTRAST_FLOOR, IMAGE_FEATURE_SCHEMA,
                                     ImageFeatureExtractor, image64,
                                     image_feature_metadata, validate_image_metadata)


def image():
    value = np.arange(64, dtype=np.uint8).reshape(8, 8) * 3 + 20
    return np.repeat(value[:, :, None], 3, axis=2)


class ImageFeatureTests(unittest.TestCase):
    def test_exact_spatial_formula_and_row_major_unmirrored_order(self):
        pixels = image()
        gray = pixels[:, :, 0].astype(np.float32) / 255
        expected = (np.clip((gray - gray.mean()) / max(float(gray.std()), CONTRAST_FLOOR), -3, 3) / 3).ravel()
        actual = image64(pixels)
        np.testing.assert_allclose(actual, expected, atol=2e-7)
        self.assertEqual(actual.shape, (64,))
        self.assertEqual(actual.dtype, np.float32)
        self.assertLess(actual[0], actual[7])
        self.assertLess(actual[7], actual[63])

    def test_true_cell_means_include_uneven_edge_pixels(self):
        pixels = np.repeat(np.arange(9, dtype=np.uint8)[None, :, None], 11, axis=0)
        pixels = np.repeat(pixels, 3, axis=2) * 20
        gray = pixels[:, :, 0].astype(np.float32) / 255
        rows, columns = np.linspace(0, 11, 9).astype(int), np.linspace(0, 9, 9).astype(int)
        grid = np.array([[gray[rows[r]:rows[r + 1], columns[c]:columns[c + 1]].mean()
                          for c in range(8)] for r in range(8)], np.float32)
        expected = (np.clip((grid - grid.mean()) / max(float(grid.std()), CONTRAST_FLOOR), -3, 3) / 3).ravel()
        np.testing.assert_allclose(image64(pixels), expected, atol=2e-7)

    def test_detector_independence_and_no_head_feet_or_warmup_gate(self):
        extractor = ImageFeatureExtractor()
        first = extractor.update(10, image(), None)
        second = extractor.update(20, image(), np.full((33, 4), np.nan))
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.any(first))
        np.testing.assert_array_equal(first, image64(image()))

    def test_uniform_images_are_honest_centered_zero_grids(self):
        for level in (0, 80, 255):
            with self.subTest(level=level):
                actual = image64(np.full((16, 16, 3), level, np.uint8))
                np.testing.assert_allclose(actual, np.zeros(64), atol=2e-6)
                self.assertTrue(np.isfinite(actual).all())

    def test_grayscale_channel_contract_and_contrast_floor(self):
        pixels = np.full((8, 8, 3), 100, np.uint8)
        pixels[0, 0] = (100, 100, 101)
        actual = image64(pixels)
        gray = (pixels.astype(np.float32) @ np.array([.114, .587, .299], np.float32)) / 255
        self.assertLess(float(gray.std()), CONTRAST_FLOOR)
        expected = ((gray - gray.mean()) / CONTRAST_FLOOR / 3).ravel()
        np.testing.assert_allclose(actual, expected, atol=1e-7)
        self.assertGreater(actual[0], 0)
        self.assertTrue((actual[1:] < 0).all())

    def test_global_brightness_shift_preserves_high_contrast_spatial_features(self):
        pixels = image()
        np.testing.assert_allclose(image64(pixels), image64(pixels + 10), atol=4e-7)

    def test_invalid_frames_and_nonmonotonic_timestamps_are_rejected(self):
        extractor = ImageFeatureExtractor()
        for bad in (None, np.zeros((7, 8, 3), np.uint8), np.zeros((8, 8), np.uint8),
                    np.zeros((8, 8, 4), np.uint8), np.zeros((8, 8, 3), np.float32)):
            with self.subTest(shape=np.shape(bad)), self.assertRaises(ValueError):
                extractor.update(1, bad)
        extractor.update(1, image())
        for stamp in (1, 0, np.nan, np.inf):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                extractor.update(stamp, image())

    def test_versioned_metadata_validates_exact_spatial_contract_with_provenance(self):
        metadata = image_feature_metadata()
        self.assertEqual(metadata['schema'], IMAGE_FEATURE_SCHEMA)
        self.assertEqual(metadata['dimension'], 64)
        self.assertEqual(metadata['joints'], [])
        self.assertFalse(metadata['required_in_frame'])
        self.assertEqual(validate_image_metadata(metadata | {'capture_source': 'local-camera'}), 'image')
        for change in ({'schema': 'pose_xy_delta64_v1'}, {'joints': [11]}, {'dimension': 32},
                       {'normalization': 'unknown'}, {'coordinates': 'mirrored'}, {'required_in_frame': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_image_metadata(metadata | change)
        for window in (0, -1, np.nan, np.inf, 'bad'):
            with self.subTest(window=window), self.assertRaises(ValueError):
                image_feature_metadata(window)


if __name__ == '__main__':
    unittest.main()
