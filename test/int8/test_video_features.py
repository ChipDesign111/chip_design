"""Partial-body video contracts and offline analysis; synthetic frames only."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.analyze_video import analyze_frames, analyze_manifest, read_frame_timestamps
from fpga.demo.features import (DEFAULT_LABELS, append_dataset, feature_metadata,
                                feature_profile_from_metadata, load_dataset)
from fpga.demo.train_camera import split_sessions
from fpga.demo.video_features import (VIDEO_FEATURE_SCHEMA, VIDEO_JOINTS,
                                     VideoFeatureExtractor, masked_observations)


def landmarks():
    points = np.full((33, 4), np.nan, np.float64)
    for index, joint in enumerate(VIDEO_JOINTS):
        points[joint] = (.2 + .05 * index, .25 + .05 * index, 0, .9)
    return points


def frame(value=80):
    pixels = np.full((12, 16, 3), value, np.uint8)
    pixels[:, 8:] = min(255, value + 40)
    return pixels


class VideoFeatureTests(unittest.TestCase):
    def test_head_and_feet_are_not_selected_and_partial_joints_are_independent(self):
        points = landmarks()
        points[11] = np.nan  # A missing shoulder must not invalidate a wrist/knee.
        points[16, 3] = .2
        points[24, 0] = 1.1
        points[26, 2] = np.nan  # z is deliberately unused.
        xy, mask = masked_observations(points)
        self.assertEqual(int(mask.sum()), 7)
        self.assertEqual(mask[VIDEO_JOINTS.index(26)], 1)
        for joint in (11, 16, 24):
            self.assertEqual(mask[VIDEO_JOINTS.index(joint)], 0)
            np.testing.assert_array_equal(xy[VIDEO_JOINTS.index(joint)], [0, 0])
        self.assertNotIn(0, VIDEO_JOINTS)
        self.assertNotIn(27, VIDEO_JOINTS)

    def test_no_detection_keeps_real_image_information_with_explicit_zero_masks(self):
        feature = VideoFeatureExtractor().update(10, frame(), None)
        self.assertEqual(feature.shape, (64,))
        self.assertEqual(feature.dtype, np.float32)
        np.testing.assert_array_equal(feature[:60], np.zeros(60, np.float32))
        self.assertGreater(feature[60], 0)
        self.assertGreater(feature[61], 0)
        self.assertTrue(np.isfinite(feature).all())

    def test_zero_coordinate_is_distinct_from_missing_observation(self):
        points = landmarks()
        points[11, :2] = (.5, .5)
        observed = VideoFeatureExtractor().update(0, frame(), points)
        missing = VideoFeatureExtractor().update(0, frame(), None)
        np.testing.assert_array_equal(observed[:2], missing[:2])
        self.assertEqual(observed[20], 1)
        self.assertEqual(missing[20], 0)

    def test_window_delta_masks_need_observations_at_both_ends(self):
        extractor = VideoFeatureExtractor()
        start = landmarks()
        start[25] = np.nan
        for stamp in np.arange(0, 1.01, .1):
            points = start.copy() if stamp == 0 else landmarks()
            points[11, 0] += stamp * .1
            feature = extractor.update(stamp, frame(int(80 + 20 * stamp)), points)
        self.assertEqual(feature[50], 1)
        self.assertAlmostEqual(float(feature[30]), .1, places=6)
        self.assertEqual(feature[50 + VIDEO_JOINTS.index(25)], 0)
        self.assertEqual(feature[30 + VIDEO_JOINTS.index(25) * 2], 0)
        self.assertGreater(feature[62], 0)
        self.assertLessEqual(float(abs(feature).max()), 1.000001)

    def test_gap_clears_temporal_evidence_but_not_current_image_or_mask(self):
        extractor = VideoFeatureExtractor()
        for stamp in np.arange(0, 1.01, .1):
            extractor.update(stamp, frame(), landmarks())
        feature = extractor.update(2, frame(120), landmarks())
        np.testing.assert_array_equal(feature[30:60], np.zeros(30))
        self.assertEqual(feature[62], 0)
        self.assertEqual(feature[20:30].sum(), 10)
        self.assertGreater(feature[60], 0)

    def test_invalid_frame_or_clock_never_becomes_a_valid_fake_observation(self):
        extractor = VideoFeatureExtractor()
        for invalid in (None, np.zeros((2, 2), np.uint8), np.zeros((2, 2, 3), np.float32)):
            with self.assertRaises(ValueError):
                extractor.update(0, invalid, None)
        extractor.update(1, frame(), None)
        for stamp in (1, 0, np.nan):
            with self.assertRaises(ValueError):
                extractor.update(stamp, frame(), None)

    def test_offline_samples_all_zero_masks_on_actual_time_without_pose_gate(self):
        timestamps = [100, 100.1, 100.26, 100.49, 100.53, 100.78]
        seen = []
        def detector(pixels, millis):
            seen.append(millis)
            return None
        features, stamps, coverage = analyze_frames([frame(i + 50) for i in range(6)], timestamps, detector)
        np.testing.assert_allclose(stamps, [100, 100.26, 100.53, 100.78])
        self.assertEqual(features.shape, (4, 64))
        self.assertEqual(coverage['frames_decoded'], 6)
        self.assertEqual(coverage['samples_with_no_observed_joints'], 4)
        self.assertEqual(coverage['mean_selected_joint_coverage'], 0)
        self.assertEqual(coverage['all_zero_feature_samples'], 0)
        self.assertEqual(len(seen), 6)
        self.assertTrue(all(a < b for a, b in zip(seen, seen[1:])))

    def test_decoded_frame_count_must_match_sidecar(self):
        for count in (1, 3):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'decoded'):
                analyze_frames([frame()] * count, [1, 1.1], lambda *_: None)

    def test_video_metadata_round_trip_and_legacy_mixing_rejected(self):
        metadata = feature_metadata(profile='video')
        self.assertEqual(metadata['schema'], VIDEO_FEATURE_SCHEMA)
        self.assertEqual(feature_profile_from_metadata(metadata), 'video')
        metadata['capture_source'] = 'local-camera'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.npz'
            x = VideoFeatureExtractor().update(1, frame(), None)[None]
            append_dataset(path, x, 'standing', 'a', [1], metadata)
            data, actual = load_dataset(path)
            np.testing.assert_array_equal(data['features'], x)
            self.assertEqual(actual, metadata)
            for profile in ('full', 'knees'):
                with self.assertRaisesRegex(ValueError, 'different feature/capture contract'):
                    append_dataset(path, x, 'standing', 'b', [2], feature_metadata(profile=profile))
        for change in ({'joints': [0] * 10}, {'layout': 'unknown'}, {'required_in_frame': True}, {'max_gap_seconds': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                feature_profile_from_metadata(metadata | change)

    def test_timestamp_reader_uses_actual_per_frame_clock_and_rejects_missing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'frames.jsonl'
            path.write_text('\n'.join(json.dumps({'frame_index': i, 'monotonic_seconds': stamp})
                                      for i, stamp in enumerate((50, 50.07, 50.21))), encoding='utf-8')
            np.testing.assert_allclose(read_frame_timestamps(path, 3), [50, 50.07, 50.21])
            with self.assertRaisesRegex(ValueError, 'count'):
                read_frame_timestamps(path, 4)
            path.write_text(json.dumps({'frame_index': 1, 'monotonic_seconds': 1}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'indices'):
                read_frame_timestamps(path, 1)

    def make_manifest(self, directory, rounds=3):
        clips = []
        for round_id in range(rounds):
            for index, label in enumerate(DEFAULT_LABELS):
                stem = f'{round_id}-{index}'
                (directory / (stem + '.avi')).write_bytes(b'synthetic video source supplied by test decoder')
                timestamps = [1000 + round_id * 100 + index * 10 + i * .1 for i in range(32)]
                clock = directory / (stem + '.frames.jsonl')
                clock.write_text('\n'.join(json.dumps({'frame_index': i, 'monotonic_seconds': stamp})
                                            for i, stamp in enumerate(timestamps)), encoding='utf-8')
                clips.append({'path': stem + '.avi', 'timestamps_path': clock.name, 'label': label,
                              'session': stem, 'status': 'complete', 'complete': True, 'frame_count': 32,
                              'fps': 99})  # Wrong nominal fps is intentionally irrelevant.
        manifest = directory / 'manifest.json'
        manifest.write_text(json.dumps({'format': 'camera_video_sessions_v1', 'labels': list(DEFAULT_LABELS),
                                        'status': 'complete', 'clips': clips}), encoding='utf-8')
        return manifest

    def test_manifest_all_no_pose_sessions_still_produce_trainable_64d_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = self.make_manifest(directory)
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            report = analyze_manifest(manifest, directory / 'actions.npz',
                                      detector_factory=lambda: contextlib.nullcontext(lambda *_: None),
                                      video_frames=lambda _: iter([frame()] * 32))
            data, contract = load_dataset(directory / 'actions.npz')
            self.assertEqual(data['features'].shape, (234, 64))
            self.assertTrue((data['features'][:, 20:30] == 0).all())
            self.assertTrue((data['features'][:, 60] > 0).all())
            self.assertEqual(contract['capture_source'], 'local-camera')
            self.assertEqual(feature_profile_from_metadata(contract), 'video')
            self.assertTrue(report['independent_holdouts_ready'])
            self.assertEqual(set(report['class_independent_sessions'].values()), {3})
            indices, assignment = split_sessions(data['labels'], data['sessions'], DEFAULT_LABELS)
            self.assertEqual(len(indices['test']), 78)
            self.assertEqual(len(assignment), 18)
            for name, contents in before.items():
                self.assertEqual((directory / name).read_bytes(), contents)
            with self.assertRaisesRegex(ValueError, 'paths must be new'):
                analyze_manifest(manifest, directory / 'actions.npz')

    def test_short_session_set_writes_quality_report_but_no_training_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = self.make_manifest(directory, rounds=1)
            with self.assertRaisesRegex(ValueError, 'three completed independent sessions'):
                analyze_manifest(manifest, directory / 'actions.npz',
                                 detector_factory=lambda: contextlib.nullcontext(lambda *_: None),
                                 video_frames=lambda _: iter([frame()] * 32))
            report = json.loads((directory / 'actions.report.json').read_text(encoding='utf-8'))
            self.assertFalse(report['independent_holdouts_ready'])
            self.assertFalse(report['dataset_written'])
            self.assertFalse((directory / 'actions.npz').exists())
            self.assertEqual(len(list(directory.glob('*.avi'))), 6)

    def test_nonempty_partial_video_is_analyzed_without_entering_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest = self.make_manifest(directory, rounds=1)
            contents = json.loads(manifest.read_text(encoding='utf-8'))
            contents['clips'] = contents['clips'][:2]
            for clip in contents['clips']:
                clip.update(complete=False, status='partial')
            contents['clips'][1]['frame_count'] = 0
            manifest.write_text(json.dumps(contents), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'three completed independent sessions'):
                analyze_manifest(manifest, directory / 'actions.npz',
                                 detector_factory=lambda: contextlib.nullcontext(lambda *_: None),
                                 video_frames=lambda _: iter([frame()] * 32))
            report = json.loads((directory / 'actions.report.json').read_text(encoding='utf-8'))
            self.assertFalse(report['dataset_written'])
            self.assertEqual(report['class_samples'], {})
            self.assertEqual(report['clips'][0]['frames_decoded'], 32)
            self.assertEqual(report['clips'][0]['samples_with_no_observed_joints'], 13)
            self.assertEqual(report['clips'][0]['training_samples'], 0)
            self.assertFalse(report['clips'][0]['included_in_dataset'])
            self.assertEqual(report['clips'][1]['frames_decoded'], 0)
            self.assertFalse((directory / 'actions.npz').exists())


if __name__ == '__main__':
    unittest.main()
