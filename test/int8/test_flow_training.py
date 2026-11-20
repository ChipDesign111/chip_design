"""Synthetic training-contract tests; no user data, video, camera or FPGA."""
import unittest

import numpy as np

from fpga.demo.flow_training import augment_flow, fit_flow_head, train_feature_scale


class FixedGeometryRng:
    """Keep spatial/amplitude jitter at identity to isolate directional physics."""
    def __init__(self, decisions):
        self.decisions = iter(decisions)
    def random(self):
        return next(self.decisions)
    def uniform(self, low, high, size=None):
        return np.zeros(size) if size is not None else (low+high)/2


class FlowTrainingTests(unittest.TestCase):
    def test_mirror_reverses_space_x_direction_and_left_right_labels(self):
        grids = np.zeros((3, 4, 4, 4), np.float32)
        grids[:, 1, 0, 0] = .6
        grids[:, 2, 1, 3] = .4
        labels = np.array([1, 2, 3])
        raw_before, labels_before = grids.copy(), labels.copy()
        raw, augmented_labels = augment_flow(grids.reshape(3, 64), labels,
                                             FixedGeometryRng([0, 1]*3))
        actual = raw.reshape(3, 4, 4, 4)
        np.testing.assert_array_equal(augmented_labels, [2, 1, 3])
        np.testing.assert_allclose(actual[:, 1, 3, 1], .6)
        np.testing.assert_allclose(actual[:, 2, 2, 3], .4)
        self.assertEqual(np.count_nonzero(actual), 6)
        np.testing.assert_array_equal(grids, raw_before)
        np.testing.assert_array_equal(labels, labels_before)

    def test_time_reversal_changes_both_direction_signs_and_keeps_labels(self):
        grid = np.zeros((1, 4, 4, 4), np.float32)
        grid[0, 0, 1, 0] = .8
        grid[0, 3, 2, 3] = .3
        raw, labels = augment_flow(grid.reshape(1, 64), np.array([1]), FixedGeometryRng([1, 0]))
        actual = raw.reshape(1, 4, 4, 4)
        self.assertEqual(labels.tolist(), [1])
        self.assertAlmostEqual(float(actual[0, 0, 1, 1]), .8)
        self.assertAlmostEqual(float(actual[0, 3, 2, 2]), .3)
        self.assertEqual(np.count_nonzero(actual), 2)

    def test_seeded_augmentation_is_reproducible_and_bounded(self):
        raw = np.linspace(0, 1, 384, dtype=np.float32).reshape(6, 64)
        labels = np.arange(6)
        a, ay = augment_flow(raw, labels, np.random.default_rng(42))
        b, by = augment_flow(raw, labels, np.random.default_rng(42))
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(ay, by)
        self.assertTrue(np.all(a >= 0) and np.all(a <= 1))

    def test_training_only_scale_matches_known_variance_and_zero_floor(self):
        train = np.zeros((2, 64), np.float32)
        train[1, 0] = 1
        scale = train_feature_scale(train)
        self.assertEqual(scale.dtype, np.float32)
        self.assertAlmostEqual(float(scale[0]), .5)
        np.testing.assert_allclose(scale[1:], .001)
        # Validation cannot affect the scale: it is not an input to the fit.
        np.testing.assert_array_equal(train_feature_scale(train), scale)
        np.testing.assert_array_equal(train_feature_scale(train[::-1]), scale)

    def test_invalid_raw_features_and_labels_rejected(self):
        for raw in (np.empty((0, 64)), np.zeros((2, 63)), np.full((2, 64), np.nan),
                    np.full((2, 64), -1), np.full((2, 64), 2)):
            with self.assertRaises(ValueError):
                train_feature_scale(raw)
        for labels in ([6], [1.5], [True], []):
            with self.assertRaises(ValueError):
                augment_flow(np.zeros((1, 64), np.float32), labels, np.random.default_rng(42))

    def test_small_synthetic_fit_preserves_train_scale_and_missing_val_class(self):
        train = np.zeros((6, 64), np.float32)
        train[np.arange(6), np.arange(6)] = .5
        labels = np.arange(6)
        result = fit_flow_head(train, labels, train[:5], labels[:5], max_epochs=3, patience=2)
        np.testing.assert_array_equal(result['train_feature_scale'], train_feature_scale(train))
        self.assertEqual(len(result['history']), result['epochs'])
        self.assertEqual(result['state_dict']['0.weight'].shape, (32, 64))
        self.assertEqual(result['state_dict']['2.weight'].shape, (6, 32))
        self.assertEqual(result['metrics']['validation']['class_counts'], [1, 1, 1, 1, 1, 0])
        self.assertIsNone(result['metrics']['validation']['recall_by_class'][5])
        self.assertEqual(result['best_epoch'], min(result['history'], key=lambda row: row['validation_loss'])['epoch'])


if __name__ == '__main__':
    unittest.main()
