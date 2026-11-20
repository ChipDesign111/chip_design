"""Camera motion features shared by offline extraction and live inference.

This frontend measures real image motion without a pose detector. Its learned
feature scales must come from training data and travel with the trained model.
"""
from collections import deque

import cv2
import numpy as np


FLOW_FEATURE_SCHEMA = 'video_hof64_v5'
FLOW_WINDOW_SECONDS = .25


def flow_feature_metadata(window_seconds=.25):
    if (not isinstance(window_seconds, (int, float, np.number)) or
            isinstance(window_seconds, (bool, np.bool_)) or
            not np.isfinite(window_seconds) or float(window_seconds) != FLOW_WINDOW_SECONDS):
        raise ValueError('HOF64 requires window_seconds=0.25')
    return {
        'schema': FLOW_FEATURE_SCHEMA, 'dimension': 64, 'joints': [],
        'window_seconds': FLOW_WINDOW_SECONDS,
        'coordinates': 'unmirrored full image; row-major 4x4 spatial cells',
        'layout': 'each cell stores mean positiveX, negativeX, positiveY, negativeY flow magnitudes',
        'image_sampling': 'cv2 BGR2GRAY then full-frame resize128x96 with INTER_AREA',
        'flow_algorithm': 'Farneback',
        'flow_parameters': {'pyr_scale': .5, 'levels': 3, 'winsize': 15,
                            'iterations': 3, 'poly_n': 5, 'poly_sigma': 1.2, 'flags': 0},
        'history_seconds': .55,
        'lag_reference': 'latest decoded frame at or before now-0.25s; earliest retained frame if none',
        'jitter_removal': 'subtract medianXY over all128x96 flow vectors',
        'deadzone_pixels': .15,
        'raw_normalization': 'clip(cell mean magnitude/(actual lag seconds*40),0,1)',
        'model_normalization': 'divide raw64 by model train_feature_scale; no centering',
        'initial_frame': 'zero64; a real frame is accepted without a visibility gate',
        'timestamps': 'actual finite strictly increasing monotonic frame-read seconds',
        'missing_pose': 'No pose detector, landmark, head, foot or complete-body requirement',
        'required_in_frame': False, 'minimum_image_shape': [1, 1],
        'accuracy_scope': 'Recorded session holdouts only; no cross-person or general human-action accuracy claim',
    }


def _feature_scale(values):
    try:
        original = np.asarray(values)
        if original.dtype.kind not in 'iuf' or original.shape != (64,):
            raise ValueError
        scale = original.astype(np.float32)
        if not np.isfinite(scale).all() or np.any(scale <= 0):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError('train_feature_scale must contain64 positive finite numbers') from error
    return scale.copy()


def validate_flow_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('Incompatible camera flow feature contract')
    expected = flow_feature_metadata(metadata.get('window_seconds', .25))
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('Incompatible camera flow feature contract')
    _feature_scale(metadata.get('train_feature_scale'))
    return 'flow'


def _flow_histogram(old_gray, current_gray, seconds):
    if seconds <= 0:
        return np.zeros(64, dtype=np.float32)
    flow = cv2.calcOpticalFlowFarneback(old_gray, current_gray, None, .5, 3, 15, 3, 5, 1.2, 0)
    flow -= np.median(flow.reshape(-1, 2), axis=0)
    channels = np.stack([
        np.maximum(flow[:, :, 0]-.15, 0), np.maximum(-flow[:, :, 0]-.15, 0),
        np.maximum(flow[:, :, 1]-.15, 0), np.maximum(-flow[:, :, 1]-.15, 0),
    ], axis=2)
    cells = channels.reshape(4, 24, 4, 32, 4).mean(axis=(1, 3)).ravel()
    return np.clip(cells/(seconds*40.0), 0, 1).astype(np.float32)


class FlowFeatureExtractor:
    """One stream's HOF64 state; start a fresh instance for every video clip.

    Every frame must be supplied, even when outputs are sampled less often.
    ``landmarks`` is accepted for the shared frontend API and is unused.
    """
    def __init__(self, window_seconds=.25, feature_scale=None):
        flow_feature_metadata(window_seconds)
        self.window_seconds = FLOW_WINDOW_SECONDS
        self.feature_scale = _feature_scale(feature_scale)
        self.last_timestamp = None
        self.last_raw = None
        self._frames = deque()

    def update(self, timestamp, frame_bgr, landmarks=None):
        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError('Frame timestamps must be finite and strictly increase') from error
        if (not np.isfinite(timestamp) or
                (self.last_timestamp is not None and timestamp <= self.last_timestamp)):
            raise ValueError('Frame timestamps must be finite and strictly increase')
        frame = np.asarray(frame_bgr)
        if (frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8 or
                frame.shape[0] < 1 or frame.shape[1] < 1):
            raise ValueError('A real uint8 BGR image is required')
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (128, 96), interpolation=cv2.INTER_AREA)
        frames = self._frames.copy()
        frames.append((timestamp, gray))
        while len(frames) > 1 and frames[1][0] < timestamp-.55:
            frames.popleft()
        available = [item for item in frames if item[0] <= timestamp-self.window_seconds]
        old_timestamp, old_gray = available[-1] if available else frames[0]
        raw = _flow_histogram(old_gray, gray, timestamp-old_timestamp)
        result = (raw/self.feature_scale).astype(np.float32)
        if result.shape != (64,) or not np.isfinite(result).all():
            raise ValueError('Invalid camera motion features')
        self._frames, self.last_timestamp, self.last_raw = frames, timestamp, raw
        return result
