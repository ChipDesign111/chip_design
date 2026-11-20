"""64D camera features that preserve partial/missing pose observations explicitly.

Every real frame produces a feature vector. Pose coverage is diagnostic, never
a capture or inference gate. The same extractor serves offline videos and live
frames; it needs neither a detector nor OpenCV itself.
"""
from collections import deque

import numpy as np

VIDEO_FEATURE_SCHEMA = 'pose_masked_video64_v3'
VIDEO_JOINTS = (11, 12, 13, 14, 15, 16, 23, 24, 25, 26)
IMAGE_SAMPLE_SHAPE = (48, 64)


def video_feature_metadata(window_seconds=1.0):
    if not np.isfinite(window_seconds) or window_seconds <= 0:
        raise ValueError('window_seconds must be finite and positive')
    return {
        'schema': VIDEO_FEATURE_SCHEMA, 'dimension': 64, 'joints': list(VIDEO_JOINTS),
        'window_seconds': float(window_seconds), 'coordinates': 'unmirrored image normalized xy',
        'normalization': 'observed xy: 2*image_fraction-1; delta: (current-old)/2; missing slots zero with explicit mask zero',
        'layout': '20 current xy, 10 observation masks, 20 window delta xy, 10 delta-valid masks, 4 real-image statistics',
        'missing_pose': 'Always emit real-frame image features; missing joints are masked; no all-joint gate',
        'visibility_threshold': 0.5, 'required_in_frame': False,
        'observation_rule': 'each joint independently finite xy/visibility, visibility>=0.5, xy inside [0,1]; z ignored',
        'temporal_rule': 'oldest frame immediately before window boundary; delta masks require both observations and full window; clear after gap>0.25s',
        'image_statistics': ['mean grayscale', 'std grayscale', 'mean absolute window change', 'left-minus-right mean absolute window change'],
        'image_sampling': '48x64 nearest samples via linspace integer indices; uint8 BGR; gray=(0.114*B+0.587*G+0.299*R)/255',
        'max_gap_seconds': 0.25,
    }


def validate_video_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('Incompatible camera video feature contract')
    expected = video_feature_metadata(metadata.get('window_seconds', 1.0))
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('Incompatible camera video feature contract')
    return 'video'


def masked_observations(landmarks, visibility=0.5):
    """Return image-normalized [10,2] values and independent [10] masks."""
    xy = np.zeros((10, 2), dtype=np.float32)
    mask = np.zeros(10, dtype=np.float32)
    if landmarks is None:
        return xy, mask
    points = np.asarray(landmarks, dtype=np.float64)
    if points.shape != (33, 4):
        raise ValueError('Expected 33 MediaPipe landmarks with x,y,z,visibility')
    selected = points[list(VIDEO_JOINTS)]
    valid = (np.isfinite(selected[:, :2]).all(axis=1) & np.isfinite(selected[:, 3]) &
             (selected[:, 3] >= visibility) & (selected[:, :2] >= 0).all(axis=1) &
             (selected[:, :2] <= 1).all(axis=1))
    xy[valid] = (selected[valid, :2] * 2 - 1).astype(np.float32)
    mask[valid] = 1
    return xy, mask


def _gray_samples(frame_bgr):
    frame = np.asarray(frame_bgr)
    if frame.ndim != 3 or frame.shape[2] != 3 or not frame.shape[0] or not frame.shape[1] or frame.dtype != np.uint8:
        raise ValueError('A nonempty real uint8 BGR frame [height,width,3] is required')
    rows = np.linspace(0, frame.shape[0] - 1, IMAGE_SAMPLE_SHAPE[0]).astype(int)
    columns = np.linspace(0, frame.shape[1] - 1, IMAGE_SAMPLE_SHAPE[1]).astype(int)
    sample = frame[rows[:, None], columns[None, :]].astype(np.float32)
    return (sample @ np.array([.114, .587, .299], np.float32)) / np.float32(255)


class VideoFeatureExtractor:
    """Stateful per-session real-frame extractor; update every captured frame.

    Frame timestamps must be actual strictly increasing monotonic seconds.
    Start a new instance for each independently labelled recording session.
    No head/feet requirement exists and absent pose detection is supported.
    """
    def __init__(self, window_seconds=1.0, max_gap=.25, visibility=.5):
        for name, value in (('window_seconds', window_seconds), ('max_gap', max_gap)):
            if not np.isfinite(value) or value <= 0:
                raise ValueError(name + ' must be finite and positive')
        if not np.isfinite(visibility) or not 0 <= visibility <= 1:
            raise ValueError('visibility must be finite inside [0,1]')
        self.window_seconds, self.max_gap, self.visibility = float(window_seconds), float(max_gap), float(visibility)
        self.samples = deque()
        self.last_timestamp = None
        self.last_observation_mask = np.zeros(10, np.float32)

    def update(self, timestamp, frame_bgr, landmarks=None):
        timestamp = float(timestamp)
        if not np.isfinite(timestamp) or (self.last_timestamp is not None and timestamp <= self.last_timestamp):
            raise ValueError('Frame timestamps must be finite and strictly increase')
        gray = _gray_samples(frame_bgr)
        xy, mask = masked_observations(landmarks, self.visibility)
        if self.last_timestamp is not None and timestamp - self.last_timestamp > self.max_gap:
            self.samples.clear()
        self.last_timestamp = timestamp
        self.last_observation_mask = mask.copy()
        self.samples.append((timestamp, xy.copy(), mask.copy(), gray))
        while len(self.samples) > 1 and self.samples[1][0] <= timestamp - self.window_seconds:
            self.samples.popleft()
        delta, delta_mask = np.zeros((10, 2), np.float32), np.zeros(10, np.float32)
        image_change, imbalance = 0.0, 0.0
        if timestamp - self.samples[0][0] >= self.window_seconds:
            _, old_xy, old_mask, old_gray = self.samples[0]
            delta_mask = mask * old_mask
            observed = delta_mask.astype(bool)
            delta[observed] = (xy[observed] - old_xy[observed]) / 2
            difference = np.abs(gray - old_gray)
            image_change = float(difference.mean())
            imbalance = float(difference[:, :32].mean() - difference[:, 32:].mean())
        image = np.array([gray.mean(), gray.std(), image_change, imbalance], np.float32)
        result = np.concatenate((xy.ravel(), mask, delta.ravel(), delta_mask, image)).astype(np.float32)
        if result.shape != (64,) or not np.isfinite(result).all():
            raise ValueError('Invalid real-frame camera features')
        return result
