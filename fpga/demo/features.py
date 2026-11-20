"""Versioned camera-only features. These are not UCI HAR sensor features."""
from collections import deque
import json
from pathlib import Path

import numpy as np

FEATURE_SCHEMA = 'pose_xy_delta64_v1'
# MediaPipe shoulders, elbows, wrists, hips, knees, ankles, heels and toes.
JOINTS = (11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)
# Six head landmarks plus shoulders, elbows, wrists, hips and knees. Feet are
# deliberately excluded so this version can be captured in a knee-up frame.
KNEES_JOINTS = (0, 2, 5, 7, 8, 9, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26)
KNEES_FEATURE_SCHEMA = 'pose_knees_xy_delta64_v2'
DEFAULT_LABELS = ('standing', 'left_arm', 'right_arm', 'both_arms', 'squat', 'lean')


def _profile_joints(profile):
    if profile == 'full':
        return JOINTS
    if profile == 'knees':
        return KNEES_JOINTS
    raise ValueError('Unknown camera feature profile: ' + str(profile))


def feature_metadata(window_seconds=1.0, profile='full'):
    if profile == 'image':
        from .image_features import image_feature_metadata
        return image_feature_metadata(window_seconds)
    if profile == 'video':
        from .video_features import video_feature_metadata
        return video_feature_metadata(window_seconds)
    joints = _profile_joints(profile)
    metadata = {'schema': FEATURE_SCHEMA, 'dimension': 64, 'joints': list(joints),
            'window_seconds': float(window_seconds), 'coordinates': 'unmirrored image pixels',
            'normalization': 'hip midpoint origin; shoulder distance unit; clip each coordinate and delta to [-3,3], divide by 3',
            'layout': '32 current normalized xy values, then 32 current-minus-window-start xy values',
            'missing_pose': 'No inference; clear history after 0.25 seconds without a valid pose',
            'visibility_threshold': 0.5}
    if profile == 'knees':
        metadata['schema'] = KNEES_FEATURE_SCHEMA
        metadata['required_in_frame'] = True
    return metadata


def feature_profile_from_metadata(metadata):
    """Resolve a known feature contract; extra capture provenance is allowed."""
    if not isinstance(metadata, dict) or metadata.get('dimension') != 64:
        raise ValueError('Incompatible camera feature schema')
    from .image_features import IMAGE_FEATURE_SCHEMA, validate_image_metadata
    if metadata.get('schema') == IMAGE_FEATURE_SCHEMA:
        return validate_image_metadata(metadata)
    from .video_features import VIDEO_FEATURE_SCHEMA, validate_video_metadata
    if metadata.get('schema') == VIDEO_FEATURE_SCHEMA:
        return validate_video_metadata(metadata)
    schemas = {FEATURE_SCHEMA: 'full', KNEES_FEATURE_SCHEMA: 'knees'}
    schema = metadata.get('schema')
    if not isinstance(schema, str) or schema not in schemas:
        raise ValueError('Incompatible camera feature schema')
    profile = schemas[schema]
    if (metadata.get('joints') != list(_profile_joints(profile)) or
            metadata.get('coordinates') != 'unmirrored image pixels'):
        raise ValueError('Incompatible camera joint/coordinate contract')
    if profile == 'knees' and metadata.get('required_in_frame') is not True:
        raise ValueError('Knees profile requires selected landmarks inside the frame')
    return profile


def normalize_pose(landmarks, image_width, image_height, visibility=0.5, profile='full'):
    """Return [16,2] pose in shoulder-width units, or None for unreliable input."""
    joints = _profile_joints(profile)
    points = np.asarray(landmarks, dtype=np.float64)
    if points.shape != (33, 4):
        raise ValueError('Expected 33 MediaPipe landmarks with x,y,z,visibility')
    if image_width <= 0 or image_height <= 0:
        raise ValueError('Image dimensions must be positive')
    selected = points[list(joints)]
    if not np.isfinite(selected).all() or (selected[:, 3] < visibility).any():
        return None
    if profile == 'knees' and ((selected[:, :2] < 0).any() or (selected[:, :2] > 1).any()):
        return None
    xy = points[:, :2] * np.array([image_width, image_height])
    scale = float(np.linalg.norm(xy[11] - xy[12]))
    if scale < max(image_width, image_height) * 0.015:
        return None
    origin = (xy[23] + xy[24]) / 2
    return ((xy[list(joints)] - origin) / scale).astype(np.float32)


class PoseWindow:
    def __init__(self, window_seconds=1.0, max_gap=0.25):
        if not np.isfinite(window_seconds) or window_seconds <= 0:
            raise ValueError('window_seconds must be positive')
        if not np.isfinite(max_gap) or max_gap <= 0:
            raise ValueError('max_gap must be positive')
        self.window_seconds = float(window_seconds)
        self.max_gap = float(max_gap)
        self.samples = deque()
        self.last_timestamp = None

    def update(self, timestamp, pose):
        timestamp = float(timestamp)
        if not np.isfinite(timestamp):
            raise ValueError('Nonfinite timestamp')
        if self.last_timestamp is not None and timestamp <= self.last_timestamp:
            raise ValueError('Timestamps must strictly increase')
        if self.samples and timestamp - self.samples[-1][0] > self.max_gap:
            self.samples.clear()
        self.last_timestamp = timestamp
        if pose is None:
            return None
        pose = np.asarray(pose, dtype=np.float32)
        if pose.shape != (16, 2) or not np.isfinite(pose).all():
            raise ValueError('Pose must be finite [16,2]')
        self.samples.append((timestamp, pose.copy()))
        # Retain the frame immediately before the exact window boundary.
        while len(self.samples) > 1 and self.samples[1][0] <= timestamp - self.window_seconds:
            self.samples.popleft()
        if timestamp - self.samples[0][0] < self.window_seconds:
            return None
        old = self.samples[0][1]
        return (np.clip(np.concatenate((pose.ravel(), (pose-old).ravel())), -3, 3) / 3).astype(np.float32)


def quantize_features(features, scale):
    data = np.asarray(features, dtype=np.float32)
    if data.shape != (64,) or not np.isfinite(data).all():
        raise ValueError('Camera input must contain 64 finite float features')
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid model input scale')
    return np.clip(np.rint(data / scale), -128, 127).astype(np.int8)


def load_dataset(path):
    with np.load(path, allow_pickle=False) as data:
        required = {'features', 'labels', 'sessions', 'timestamps', 'metadata'}
        if not required.issubset(data.files):
            raise ValueError('Dataset missing ' + ', '.join(sorted(required-set(data.files))))
        result = {name: data[name].copy() for name in required if name != 'metadata'}
        metadata = json.loads(str(data['metadata'].item()))
    x = result['features']
    if x.ndim != 2 or x.shape[1] != 64 or not np.isfinite(x).all():
        raise ValueError('Dataset features must be finite [samples,64]')
    if not len(x) or any(result[name].shape != (len(x),) for name in ('labels', 'sessions', 'timestamps')):
        raise ValueError('Dataset arrays have inconsistent or empty sample count')
    feature_profile_from_metadata(metadata)
    if not np.isfinite(result['timestamps']).all():
        raise ValueError('Nonfinite dataset timestamps')
    return result, metadata


def append_dataset(path, features, label, session, timestamps, metadata):
    path = Path(path)
    x = np.asarray(features, dtype=np.float32)
    ts = np.asarray(timestamps, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 64 or not len(x) or not np.isfinite(x).all():
        raise ValueError('No valid 64-dimensional feature samples to save')
    if ts.shape != (len(x),) or not np.isfinite(ts).all():
        raise ValueError('Timestamp count differs from feature samples')
    if not label or not session:
        raise ValueError('Label and session must not be empty')
    arrays = {'features': x, 'timestamps': ts,
              'labels': np.array([label]*len(x)), 'sessions': np.array([session]*len(x))}
    if path.exists():
        old, prior_meta = load_dataset(path)
        if prior_meta != metadata:
            raise ValueError('Existing dataset uses a different feature/capture contract')
        existing_labels = set(old['labels'][old['sessions'] == session])
        if existing_labels - {label}:
            raise ValueError('A session must contain only one action class')
        arrays = {name: np.concatenate((old[name], value)) for name, value in arrays.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write a temporary file in the same directory, then atomically replace.
    temporary = path.with_name(path.name + '.tmp.npz')
    np.savez_compressed(temporary, **arrays, metadata=np.array(json.dumps(metadata, sort_keys=True)))
    temporary.replace(path)
    return len(arrays['features'])
