"""Synthetic HOF64 contract/state tests: no camera, videos or FPGA."""
import unittest
from unittest.mock import patch

import numpy as np

from fpga.demo.flow_features import (
    FlowFeatureExtractor, _flow_histogram, flow_feature_metadata,
    validate_flow_metadata,
)


class CameraFlowFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((96, 128, 3), np.uint8)

    def test_contract_requires_fixed_algorithm_and_training_scales(self):
        contract = flow_feature_metadata(.25)
        with self.assertRaises(ValueError):
            validate_flow_metadata(contract)
        contract['train_feature_scale'] = np.ones(64).tolist()
        contract['capture_source'] = 'local actual videos'
        self.assertEqual(validate_flow_metadata(contract), 'flow')
        contract['deadzone_pixels'] = .2
        with self.assertRaises(ValueError):
            validate_flow_metadata(contract)
        for window in (0, 1, .5, True, np.nan, '0.25'):
            with self.assertRaises(ValueError):
                flow_feature_metadata(window)

    def test_scale_validation_and_private_copy(self):
        for scale in (None, np.ones(63), np.ones((1, 64)), ['1']*64,
                      [True]*64, [0]*64, [-1]*64, [np.inf]*64):
            with self.assertRaises(ValueError):
                FlowFeatureExtractor(feature_scale=scale)
        scale = np.ones(64)
        extractor = FlowFeatureExtractor(feature_scale=scale)
        scale[:] = 0
        np.testing.assert_array_equal(extractor.feature_scale, np.ones(64))

    def test_first_frame_accepted_and_landmarks_are_unused(self):
        extractor = FlowFeatureExtractor(feature_scale=np.ones(64))
        with patch('fpga.demo.flow_features.cv2.calcOpticalFlowFarneback') as calculate:
            feature = extractor.update(10, self.frame, landmarks=object())
        calculate.assert_not_called()
        self.assertEqual(feature.dtype, np.float32)
        np.testing.assert_array_equal(feature, np.zeros(64))

    def test_global_translation_is_removed_as_jitter(self):
        flow = np.empty((96, 128, 2), np.float32)
        flow[:] = (3, -2)
        with patch('fpga.demo.flow_features.cv2.calcOpticalFlowFarneback', return_value=flow):
            raw = _flow_histogram(self.frame[:, :, 0], self.frame[:, :, 0], .25)
        np.testing.assert_array_equal(raw, np.zeros(64))

    def test_cell_sign_deadzone_lag_speed_and_scale(self):
        flow = np.zeros((96, 128, 2), np.float32)
        flow[:24, :32, 0] = 2.15
        flow[24:48, 32:64, 1] = -1.15
        flow[48:72, 64:96, 0] = .1
        extractor = FlowFeatureExtractor(feature_scale=np.full(64, .5))
        extractor.update(0, self.frame)
        with patch('fpga.demo.flow_features.cv2.calcOpticalFlowFarneback', return_value=flow):
            actual = extractor.update(.25, self.frame)
        raw = extractor.last_raw.reshape(4, 4, 4)
        self.assertAlmostEqual(float(raw[0, 0, 0]), .2, places=5)
        self.assertAlmostEqual(float(raw[1, 1, 3]), .1, places=5)
        self.assertEqual(np.count_nonzero(raw), 2)
        np.testing.assert_allclose(actual, extractor.last_raw*2)

    def test_irregular_clock_uses_latest_frame_before_lag(self):
        extractor = FlowFeatureExtractor(feature_scale=np.ones(64))
        observed = []
        def inspect(old, current, seconds):
            observed.append((int(old[0, 0]), int(current[0, 0]), seconds))
            return np.zeros(64, np.float32)
        with patch('fpga.demo.flow_features._flow_histogram', side_effect=inspect):
            for stamp, value in [(0, 10), (.1, 20), (.26, 30), (.4, 40), (1., 50)]:
                extractor.update(stamp, np.full_like(self.frame, value))
        self.assertEqual(observed[2][:2], (10, 30))
        self.assertEqual(observed[3][:2], (20, 40))
        self.assertAlmostEqual(observed[3][2], .3)
        self.assertEqual(observed[4][:2], (40, 50))
        self.assertAlmostEqual(observed[4][2], .6)

    def test_bad_frame_or_clock_does_not_advance_stream(self):
        extractor = FlowFeatureExtractor(feature_scale=np.ones(64))
        extractor.update(1, self.frame)
        for stamp in (1, 0, np.nan, np.inf, None):
            with self.assertRaises(ValueError):
                extractor.update(stamp, self.frame)
        for frame in (None, np.zeros((0, 5, 3), np.uint8), self.frame.astype(float), self.frame[:, :, 0]):
            with self.assertRaises(ValueError):
                extractor.update(2, frame)
        self.assertEqual(extractor.last_timestamp, 1)
        self.assertEqual(len(extractor._frames), 1)
        np.testing.assert_array_equal(extractor.update(2, self.frame), np.zeros(64))

    def test_raw_frame_pixels_are_never_modified(self):
        rng = np.random.default_rng(42)
        frames = rng.integers(0, 256, (2, 96, 128, 3), np.uint8)
        original = frames.copy()
        extractor = FlowFeatureExtractor(feature_scale=np.ones(64))
        for i, frame in enumerate(frames):
            result = extractor.update(i*.25, frame)
            self.assertTrue(np.isfinite(result).all())
        np.testing.assert_array_equal(frames, original)


if __name__ == '__main__':
    unittest.main()
