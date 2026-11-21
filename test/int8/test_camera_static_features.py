"""Static landmark contract tests with a fake detector, never camera/FPGA I/O.

The numeric feature tests use pixel landmarks directly. Runtime tests replace
the model loader and predict call; no checkpoint download or YOLO inference runs.
"""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fpga.demo import static_features as static
from fpga.demo.features import feature_metadata, feature_profile_from_metadata


def body_points():
    """Only shoulders and hips visible; no head, wrists, knees, or feet needed."""
    points = np.zeros((17, 3), np.float32)
    points[5] = (200, 100, 1)
    points[6] = (400, 100, 1)
    points[11] = (200, 300, 1)
    points[12] = (400, 300, 1)
    return points


BOX = np.array([100, 50, 500, 450], np.float32)


class TensorStub:
    def __init__(self, data):
        self.data = np.asarray(data)

    def cpu(self):
        return self

    def numpy(self):
        return self.data


class BoxesStub:
    def __init__(self, box=None):
        self.xyxy = [] if box is None else [TensorStub(box)]

    def __len__(self):
        return len(self.xyxy)


def detection(points=None, box=None):
    return SimpleNamespace(boxes=BoxesStub(box),
                           keypoints=SimpleNamespace(data=[] if points is None else [TensorStub(points)]))


class StaticFeatureNumericTests(unittest.TestCase):
    def test_exact_layout_has_independently_expected_xy_bones_masks_and_globals(self):
        row = static.feature(body_points(), BOX, 640, 480)
        expected = np.zeros(64, np.float32)
        xy = expected[:20].reshape(10, 2)
        xy[0], xy[1], xy[6], xy[7] = (-1/6, -1/3), (1/6, -1/3), (-1/6, 0), (1/6, 0)
        expected[20:30][[0, 1, 6, 7]] = 1
        bones = expected[30:50].reshape(10, 2)
        bones[0], bones[1], bones[6], bones[7] = (0, -1/3), (0, -1/3), (-1/3, 0), (1/3, 0)
        expected[50:60][[0, 1, 6, 7]] = 1
        expected[60:] = [400/640, 400/480, 1, .4]
        self.assertEqual(row.shape, (64,))
        self.assertEqual(row.dtype, np.float32)
        np.testing.assert_allclose(row, expected, rtol=0, atol=3e-8)

    def test_missing_head_and_feet_are_irrelevant_even_nonfinite(self):
        points = body_points()
        original = static.feature(points, BOX, 640, 480)
        points[:5] = np.nan
        points[15:] = np.inf
        np.testing.assert_array_equal(static.feature(points, BOX, 640, 480), original)
        self.assertEqual(int(original[20:30].sum()), 4)

    def test_border_shoulder_mask_does_not_change_hip_scale_or_other_coordinates(self):
        points = body_points()
        points[5] = (640*.03, 100, 1)  # high confidence, but clipped by frame boundary
        points[7] = (240, 200, 1)      # elbow whose parent is that shoulder
        edge = static.feature(points, BOX, 640, 480)
        hidden = points.copy()
        hidden[5] = (300, 150, 0)     # different coordinates, explicitly missing
        np.testing.assert_array_equal(static.feature(hidden, BOX, 640, 480), edge)
        self.assertEqual(edge[20], 0)
        np.testing.assert_array_equal(edge[:2], [0, 0])
        self.assertEqual(edge[22], 1)   # elbow itself remains a valid observation
        self.assertEqual(edge[52], 0)   # its bone needs both elbow and shoulder
        np.testing.assert_array_equal(edge[34:36], [0, 0])
        np.testing.assert_allclose(edge[12:16], [-1/6, 0, 1/6, 0], rtol=0, atol=3e-8)
        self.assertEqual(edge[62], 1)

    def test_actual_zero_coordinate_is_distinct_from_missing_zero(self):
        points = np.zeros((17, 3), np.float32)
        points[11] = (300, 300, 1)  # single visible hip defines the origin
        row = static.feature(points, BOX, 640, 480)
        np.testing.assert_array_equal(row[12:14], [0, 0])
        self.assertEqual(row[26], 1)  # a real zero offset has mask one
        np.testing.assert_array_equal(row[8:10], [0, 0])
        self.assertEqual(row[24], 0)  # missing wrist has mask zero
        self.assertEqual(row[56], 0)  # no invented hip-to-hip bone
        self.assertEqual(row[62], 0)  # not a valid hip pair

    def test_hip_pair_is_preferred_to_wide_shoulders_as_scale(self):
        points = body_points()
        before = static.feature(points, BOX, 640, 480)
        points[5, 0], points[6, 0] = 50, 590
        after = static.feature(points, BOX, 640, 480)
        np.testing.assert_array_equal(after[12:16], before[12:16])
        np.testing.assert_allclose(after[:2], [-250/200/3, -200/200/3], rtol=0, atol=6e-8)

    def test_shoulder_then_box_scale_fallbacks_are_defined_for_partial_people(self):
        shoulders = body_points()
        shoulders[11:13, 2] = 0
        row = static.feature(shoulders, BOX, 640, 480)
        np.testing.assert_allclose(row[:4], [-1/6, 0, 1/6, 0], rtol=0, atol=3e-8)
        self.assertEqual(row[62], 0)
        wrist = np.zeros((17, 3), np.float32)
        wrist[9] = (380, 250, 1)
        # No hips/shoulder pair: box centre (300,250), unit .4*400=160.
        row = static.feature(wrist, BOX, 640, 480)
        np.testing.assert_allclose(row[8:10], [1/6, 0], rtol=0, atol=3e-8)
        self.assertEqual(row[24], 1)

    def test_confidence_and_boundary_thresholds_are_inclusive_and_masks_clear_bones(self):
        points = np.zeros((17, 3), np.float32)
        points[5], points[6] = (40, 32, .25), (960, 768, .25)
        row = static.feature(points, [0, 0, 1000, 800], 1000, 800)
        self.assertEqual(row[20:22].tolist(), [1, 1])
        points[5, 0], points[6, 2] = 39, .249
        row = static.feature(points, [0, 0, 1000, 800], 1000, 800)
        self.assertFalse(row[20:30].any())
        self.assertFalse(row[:20].any())
        self.assertFalse(row[30:60].any())

    def test_input_landmarks_are_not_modified_and_nonfinite_selected_joints_are_masked(self):
        points = body_points()
        points[7] = (np.nan, 140, 1)
        points[9] = (200, 140, np.inf)
        original, original_box = points.copy(), BOX.copy()
        row = static.feature(points, BOX, 640, 480)
        self.assertTrue(np.isfinite(row).all())
        self.assertEqual(row[22], 0)
        self.assertEqual(row[24], 0)
        np.testing.assert_array_equal(points, original)
        np.testing.assert_array_equal(BOX, original_box)

    def test_malformed_shapes_dimensions_and_nonfinite_boxes_are_rejected(self):
        for points, box, width, height in (
                (np.zeros((16, 3)), BOX, 640, 480), (body_points(), [1,2,3], 640, 480),
                (body_points(), BOX, 0, 480), (body_points(), BOX, 640, -1),
                (body_points(), [0,0,np.nan,480], 640, 480)):
            with self.subTest(width=width, height=height, box=box):
                with self.assertRaises(ValueError):
                    static.feature(points, box, width, height)


class StaticFeatureContractTests(unittest.TestCase):
    def test_contract_binds_asset_layout_and_all_detector_parameters(self):
        contract = static.static_feature_metadata()
        self.assertEqual(contract['dimension'], 64)
        self.assertEqual(contract['detector_asset_sha256'], static.MODEL_SHA256)
        self.assertEqual(contract['parents'], [6,7,0,1,2,3,7,6,6,7])
        self.assertEqual(static.validate_static_metadata(contract), 'static')
        self.assertEqual(feature_profile_from_metadata(contract), 'static')
        self.assertEqual(feature_metadata(.25, profile='static'), contract)
        for key in contract:
            changed = copy.deepcopy(contract)
            changed[key] = 'different'
            with self.subTest(field=key):
                with self.assertRaises(ValueError):
                    static.validate_static_metadata(changed)
                with self.assertRaises(ValueError):
                    feature_profile_from_metadata(changed)
            omitted = copy.deepcopy(contract)
            del omitted[key]
            with self.subTest(missing=key):
                with self.assertRaises(ValueError):
                    static.validate_static_metadata(omitted)
        with_provenance = dict(contract, capture_source='local-camera')
        self.assertEqual(static.validate_static_metadata(with_provenance), 'static')

    def test_only_exact_static_window_contract_is_accepted(self):
        for window in (0, .249, .25001, 1, float('nan'), float('inf'), True, '.25', None):
            with self.subTest(window=window):
                with self.assertRaises(ValueError):
                    static.static_feature_metadata(window)
        self.assertEqual(static.static_feature_metadata(np.float32(.25))['window_seconds'], .25)
        for invalid in (None, [], 'not a contract'):
            with self.assertRaises(ValueError):
                static.validate_static_metadata(invalid)

    def test_missing_or_mismatched_asset_is_rejected_before_detector_import(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'wrong-asset.pt'
            with self.assertRaisesRegex(ValueError, 'asset'):
                static._load_pose_model(path)
            path.write_bytes(b'not the pinned official checkpoint')
            with self.assertRaisesRegex(ValueError, 'asset'):
                static._load_pose_model(path)


class StaticFeatureRuntimeTests(unittest.TestCase):
    def create(self, outputs):
        detector = SimpleNamespace(predict=Mock(side_effect=[[result] for result in outputs]))
        loader = patch.object(static, '_load_pose_model', return_value=detector)
        mocked = loader.start()
        self.addCleanup(loader.stop)
        extractor = static.StaticPoseFeatureExtractor('test-only-model.pt')
        mocked.assert_called_once_with('test-only-model.pt')
        return extractor, detector

    def test_first_static_frame_is_immediate_and_identical_pose_needs_no_motion_history(self):
        person = detection(body_points(), BOX)
        extractor, detector = self.create([person, person, person])
        frame = np.zeros((480, 640, 3), np.uint8)
        first = extractor.update(100, frame)
        self.assertIsNotNone(first)
        expected = static.feature(body_points(), BOX, 640, 480)
        np.testing.assert_array_equal(first, expected)
        np.testing.assert_array_equal(extractor.update(100.001, frame), first)
        np.testing.assert_array_equal(extractor.update(100.002, frame, landmarks='unused'), first)
        self.assertEqual(detector.predict.call_count, 3)
        self.assertIs(detector.predict.call_args.args[0], frame)
        self.assertEqual(detector.predict.call_args.kwargs,
                         dict(imgsz=416, conf=.25, max_det=1, device='cpu', verbose=False))

    def test_no_person_and_no_usable_joints_return_none_instead_of_standing_or_old_pose(self):
        extractor, _ = self.create([detection(body_points(), BOX), detection(),
                                    detection(np.zeros((17,3), np.float32), BOX)])
        frame = np.zeros((480, 640, 3), np.uint8)
        self.assertIsNotNone(extractor.update(1, frame))
        self.assertIsNone(extractor.update(1.1, frame))
        self.assertIsNone(extractor.update(1.2, frame))

    def test_changed_static_pose_affects_first_following_frame_without_temporal_warmup(self):
        changed = body_points()
        changed[7], changed[9] = (200, 60, 1), (200, 30, 1)
        extractor, _ = self.create([detection(body_points(), BOX), detection(changed, BOX)])
        frame = np.zeros((480, 640, 3), np.uint8)
        first, next_ = extractor.update(1, frame), extractor.update(1.001, frame)
        self.assertIsNotNone(next_)
        self.assertFalse(np.array_equal(next_, first))
        np.testing.assert_array_equal(next_, static.feature(changed, BOX, 640, 480))

    def test_timestamp_is_finite_strictly_increasing_even_across_no_person_frames(self):
        extractor, detector = self.create([detection(), detection(body_points(), BOX)])
        frame = np.zeros((480, 640, 3), np.uint8)
        self.assertIsNone(extractor.update(10, frame))
        for timestamp in (10, 9, float('nan'), float('inf'), float('-inf')):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    extractor.update(timestamp, frame)
        self.assertEqual(detector.predict.call_count, 1)
        self.assertIsNotNone(extractor.update(10.01, frame))

    def test_invalid_images_are_rejected_without_predicting_or_consuming_timestamp(self):
        extractor, detector = self.create([detection(body_points(), BOX)])
        for frame in (np.zeros((480,640), np.uint8), np.zeros((480,640,4), np.uint8),
                      np.zeros((480,640,3), np.float32), np.zeros((0,640,3), np.uint8)):
            with self.subTest(shape=frame.shape, dtype=frame.dtype):
                with self.assertRaises(ValueError):
                    extractor.update(10, frame)
        self.assertEqual(detector.predict.call_count, 0)
        self.assertIsNone(extractor.last_timestamp)
        self.assertIsNotNone(extractor.update(10, np.zeros((480,640,3), np.uint8)))


if __name__ == '__main__':
    unittest.main()
