"""Experimental camera-specific 64D spatial image features.

This extractor uses each real image directly. It has no detector, landmark,
head, foot or complete-body requirement. Fixed camera/session holdouts are
still needed; this representation establishes no general human accuracy.
"""
import numpy as np

IMAGE_FEATURE_SCHEMA = 'image_grid64_v4'
GRID_SHAPE = (8, 8)
CONTRAST_FLOOR = 16 / 255


def image_feature_metadata(window_seconds=1.0):
    if not isinstance(window_seconds, (int, float, np.number)) or not np.isfinite(window_seconds) or window_seconds <= 0:
        raise ValueError('window_seconds must be finite and positive')
    return {
        'schema': IMAGE_FEATURE_SCHEMA, 'dimension': 64, 'joints': [],
        'window_seconds': float(window_seconds),
        'window_role': 'compatibility field only; this extractor uses one current frame without temporal history',
        'coordinates': 'unmirrored image grayscale grid, row-major top-to-bottom then left-to-right',
        'layout': '8x8 grayscale cell means, centered and contrast normalized, flattened to 64 values',
        'image_sampling': 'cell edges=floor(linspace(0,size,9)); mean every pixel in each nonoverlapping cell',
        'grayscale': '(0.114*B+0.587*G+0.299*R)/255 from uint8 BGR pixels, float32 arithmetic',
        'normalization': 'subtract mean of 64 cell means; divide by max(std of 64 cell means,16/255); clip to [-3,3]; divide by 3',
        'missing_pose': 'No pose detector or observation mask is used; every real frame yields image features',
        'required_in_frame': False, 'minimum_image_shape': [8, 8],
        'accuracy_scope': 'Camera-specific spatial appearance; independent recorded-session holdouts required; no cross-person claim',
    }


def validate_image_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('Incompatible camera image feature contract')
    expected = image_feature_metadata(metadata.get('window_seconds', 1.0))
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('Incompatible camera image feature contract')
    return 'image'


def image64(frame_bgr):
    """Compute 64 real-image features; no state, detector or hidden resize step."""
    frame = np.asarray(frame_bgr)
    if (frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8 or
            frame.shape[0] < GRID_SHAPE[0] or frame.shape[1] < GRID_SHAPE[1]):
        raise ValueError('A real uint8 BGR image of at least 8x8 pixels is required')
    pixels = frame.astype(np.float32)
    gray = (pixels @ np.array([.114, .587, .299], np.float32)) / np.float32(255)
    row_edges = np.linspace(0, frame.shape[0], 9).astype(int)
    column_edges = np.linspace(0, frame.shape[1], 9).astype(int)
    grid = np.empty(GRID_SHAPE, np.float32)
    for row in range(8):
        for column in range(8):
            grid[row, column] = gray[row_edges[row]:row_edges[row + 1],
                                     column_edges[column]:column_edges[column + 1]].mean()
    centered = grid - grid.mean()
    scale = max(float(grid.std()), CONTRAST_FLOOR)
    result = (np.clip(centered / scale, -3, 3) / np.float32(3)).ravel().astype(np.float32)
    if result.shape != (64,) or not np.isfinite(result).all():
        raise ValueError('Invalid camera image features')
    return result


class ImageFeatureExtractor:
    """Shared offline/live API; the optional landmarks argument is ignored.

    Timestamps must be actual monotonic seconds. No warmup, visibility gate or
    temporal dependency is present. Uniform real images correctly produce a
    centered zero grid; this does not claim a detected valid skeleton.
    """
    def __init__(self, window_seconds=1.0):
        image_feature_metadata(window_seconds)
        self.window_seconds = float(window_seconds)
        self.last_timestamp = None

    def update(self, timestamp, frame_bgr, landmarks=None):
        timestamp = float(timestamp)
        if not np.isfinite(timestamp) or (self.last_timestamp is not None and timestamp <= self.last_timestamp):
            raise ValueError('Frame timestamps must be finite and strictly increase')
        result = image64(frame_bgr)
        self.last_timestamp = timestamp
        return result
