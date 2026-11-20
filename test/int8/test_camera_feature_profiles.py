"""Versioned full-body and knee-up camera contracts; no camera hardware needed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.features import (FEATURE_SCHEMA, JOINTS, KNEES_JOINTS, PoseWindow,
                                append_dataset, feature_metadata,
                                feature_profile_from_metadata, load_dataset,
                                normalize_pose)


def landmarks():
    points = np.zeros((33, 4), dtype=np.float64)
    points[:, :2] = (.5, .4)
    points[:, 3] = 1
    for index, joint in enumerate((0, 2, 5, 7, 8, 9)):
        points[joint, :2] = (.43 + index * .025, .12 + (index % 2) * .02)
    for left, right, y in ((11, 12, .28), (13, 14, .4), (15, 16, .5),
                           (23, 24, .57), (25, 26, .8), (27, 28, .94),
                           (29, 30, .96), (31, 32, .98)):
        points[left, :2], points[right, :2] = (.35, y), (.65, y)
    return points


class CameraFeatureProfileTests(unittest.TestCase):
    def test_full_metadata_is_legacy_contract(self):
        expected = {
            'schema': 'pose_xy_delta64_v1', 'dimension': 64,
            'joints': [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32],
            'window_seconds': 1.0, 'coordinates': 'unmirrored image pixels',
            'normalization': 'hip midpoint origin; shoulder distance unit; clip each coordinate and delta to [-3,3], divide by 3',
            'layout': '32 current normalized xy values, then 32 current-minus-window-start xy values',
            'missing_pose': 'No inference; clear history after 0.25 seconds without a valid pose',
            'visibility_threshold': 0.5,
        }
        self.assertEqual(FEATURE_SCHEMA, expected['schema'])
        self.assertEqual(feature_metadata(), expected)
        self.assertEqual(feature_metadata(profile='full'), expected)
        self.assertEqual(feature_profile_from_metadata(expected), 'full')

    def test_full_pose_keeps_legacy_selection_and_out_of_frame_behavior(self):
        points = landmarks()
        # Head was not part of v1, and v1 did not enforce image bounds.
        points[0] = np.nan
        points[31, :2] = (-.1, 1.1)
        xy = points[:, :2] * (1280, 720)
        expected = ((xy[list(JOINTS)] - (xy[23] + xy[24]) / 2) /
                    np.linalg.norm(xy[11] - xy[12])).astype(np.float32)
        np.testing.assert_array_equal(normalize_pose(points, 1280, 720), expected)

    def test_knees_does_not_require_ankles_heels_or_toes(self):
        clean = landmarks()
        cropped = clean.copy()
        cropped[27:33] = np.nan
        cropped[27:33, :2] = (-2, 3)
        cropped[27:33, 3] = 0
        actual = normalize_pose(cropped, 1280, 720, profile='knees')
        self.assertIsNotNone(actual)
        np.testing.assert_array_equal(actual, normalize_pose(clean, 1280, 720, profile='knees'))
        self.assertIsNone(normalize_pose(cropped, 1280, 720))

    def test_knees_requires_visible_finite_head_and_knees_inside_frame(self):
        for joint in (0, 2, 5, 7, 8, 9, 25, 26):
            for column, value in ((3, .49), (0, np.nan), (2, np.inf),
                                   (0, -.001), (0, 1.001), (1, -.001), (1, 1.001)):
                with self.subTest(joint=joint, column=column, value=value):
                    points = landmarks()
                    points[joint, column] = value
                    self.assertIsNone(normalize_pose(points, 1280, 720, profile='knees'))
        points = landmarks()
        points[0, :2] = (0, 1)
        self.assertIsNotNone(normalize_pose(points, 1280, 720, profile='knees'))

    def test_knees_normalization_and_window_keep_64d_shape(self):
        points = landmarks()
        base = normalize_pose(points, 1280, 720, profile='knees')
        translated_scaled = points.copy()
        translated_scaled[:, :2] = points[:, :2] * .7 + .1
        np.testing.assert_allclose(base, normalize_pose(translated_scaled, 1280, 720, profile='knees'), atol=1e-6)
        wider = points.copy()
        wider[:, 0] /= 2
        np.testing.assert_allclose(base, normalize_pose(wider, 2560, 720, profile='knees'), atol=1e-6)
        self.assertEqual(base.shape, (16, 2))
        self.assertEqual(base.dtype, np.float32)
        window = PoseWindow()
        for timestamp in np.linspace(0, 1, 11):
            feature = window.update(timestamp, base)
        self.assertEqual(feature.shape, (64,))
        self.assertEqual(feature.dtype, np.float32)
        np.testing.assert_array_equal(feature[32:], np.zeros(32, np.float32))

    def test_both_contracts_round_trip_with_capture_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            for profile in ('full', 'knees'):
                with self.subTest(profile=profile):
                    path = Path(directory) / (profile + '.npz')
                    metadata = feature_metadata(.75, profile=profile)
                    metadata['capture_source'] = {'backend': 'DSHOW', 'width': 1280, 'height': 720}
                    features = np.arange(128, dtype=np.float32).reshape(2, 64) / 128
                    self.assertEqual(append_dataset(path, features, 'standing', 'session-a', [1, 2], metadata), 2)
                    loaded, actual = load_dataset(path)
                    np.testing.assert_array_equal(loaded['features'], features)
                    self.assertEqual(actual, metadata)
                    self.assertEqual(feature_profile_from_metadata(actual), profile)
                    self.assertEqual(append_dataset(path, features[:1], 'standing', 'session-a', [3], metadata), 3)

    def test_mixed_profile_append_rejected_without_changing_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'actions.npz'
            features = np.zeros((1, 64), np.float32)
            append_dataset(path, features, 'standing', 'session-a', [1], feature_metadata())
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'different feature/capture contract'):
                append_dataset(path, features, 'standing', 'session-b', [2], feature_metadata(profile='knees'))
            self.assertEqual(path.read_bytes(), original)

    def test_resolver_and_loader_reject_inconsistent_contracts(self):
        self.assertEqual(tuple(feature_metadata(profile='knees')['joints']), KNEES_JOINTS)
        mutations = (
            {'schema': 'unknown-v3'}, {'schema': []}, {'dimension': 32}, {'joints': list(JOINTS)},
            {'coordinates': 'mirrored image pixels'}, {'required_in_frame': False},
            {'required_in_frame': 1},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.npz'
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    metadata = feature_metadata(profile='knees') | mutation
                    with self.assertRaises(ValueError):
                        feature_profile_from_metadata(metadata)
                    np.savez_compressed(path, features=np.zeros((1, 64), np.float32),
                                        labels=np.array(['standing']), sessions=np.array(['a']),
                                        timestamps=np.array([1.0]), metadata=np.array(json.dumps(metadata)))
                    with self.assertRaises(ValueError):
                        load_dataset(path)
        for operation in (lambda: feature_metadata(profile='unknown'),
                          lambda: normalize_pose(landmarks(), 1280, 720, profile='unknown')):
            with self.assertRaisesRegex(ValueError, 'Unknown camera feature profile'):
                operation()


if __name__ == '__main__':
    unittest.main()
