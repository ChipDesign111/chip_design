"""PC-only partial-person landmarks; the six-action head runs on the FPGA."""
import hashlib
from pathlib import Path

import numpy as np

SCHEMA = 'yolo11_hip_mask_static64_v1'
JOINTS = tuple(range(5, 15))
PARENTS = np.array([6, 7, 0, 1, 2, 3, 7, 6, 6, 7])
MODEL_URL = 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt'
MODEL_SHA256 = '869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0'
DEFAULT_STATIC_MODEL = Path('tools/local/camera_demo/yolo_pose_static_20261121/assets/yolo11n-pose.pt')


def static_feature_metadata(window_seconds=.25):
    if isinstance(window_seconds, (bool, np.bool_)) or not isinstance(window_seconds, (int, float, np.number)) or window_seconds != .25:
        raise ValueError('Static pose profile requires window_seconds=0.25')
    return dict(schema=SCHEMA, dimension=64, joints=list(JOINTS), window_seconds=.25,
                coordinates='unmirrored original image pixels; COCO17',
                layout='20hip-relative xy,10joint masks,20parent-bone xy,10bone masks,4box/hip/mask statistics',
                parents=PARENTS.tolist(), confidence_threshold=.25, boundary_fraction=.04,
                origin='hip midpoint; single hip; shoulder midpoint; box midpoint',
                scale='hip width >=max(12px,0.025W); shoulder width with same threshold; max(0.4boxwidth,20px)',
                normalization='clip xy/bones in scale units to [-3,3], divide by3; missing coordinates zero with mask0',
                globals='boxwidth/W,boxheight/H,bothhipsvalid,mean10jointmask',
                detector='YOLO11n-pose', detector_asset_sha256=MODEL_SHA256,
                detector_image_size=416, detector_person_confidence=.25, detector_max_people=1,
                temporal='instantaneous static pose; no motion history required',
                required_in_frame=False, missing_pose='partial joints accepted; no person or no usable body joints yields no inference',
                accuracy_scope='personal calibration and development checks; no general action accuracy claim')


def validate_static_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('Incompatible static pose feature contract')
    expected = static_feature_metadata(metadata.get('window_seconds', .25))
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('Incompatible static pose feature contract')
    return 'static'


def feature(points, box, width, height):
    """Deterministic 64D features; missing head and feet never reject a person."""
    if points is None or box is None:
        return np.zeros(64, np.float32)
    points, box = np.asarray(points, np.float32), np.asarray(box, np.float32)
    if points.shape != (17, 3) or box.shape != (4,) or width <= 0 or height <= 0:
        raise ValueError('Expected COCO17 pixel xy/confidence, xyxy personbox and positive image dimensions')
    xy, confidence = points[5:15, :2], points[5:15, 2]
    valid = (np.isfinite(xy).all(1) & np.isfinite(confidence) & (confidence >= .25) &
             (xy[:, 0] >= width * .04) & (xy[:, 0] <= width * .96) &
             (xy[:, 1] >= height * .04) & (xy[:, 1] <= height * .96))
    hips, shoulders = bool(valid[6] and valid[7]), bool(valid[0] and valid[1])
    if hips:
        origin = xy[[6, 7]].mean(0)
    elif valid[6] or valid[7]:
        origin = xy[6] if valid[6] else xy[7]
    elif shoulders:
        origin = xy[[0, 1]].mean(0)
    else:
        origin = (box[:2] + box[2:]) / 2
    hip_width = float(np.linalg.norm(xy[6] - xy[7])) if hips else 0
    shoulder_width = float(np.linalg.norm(xy[0] - xy[1])) if shoulders else 0
    if hip_width >= max(12, width * .025):
        unit = hip_width
    elif shoulder_width >= max(12, width * .025):
        unit = shoulder_width
    else:
        unit = max(float(box[2] - box[0]) * .4, 20)
    current, bones = np.zeros((10, 2), np.float32), np.zeros((10, 2), np.float32)
    current[valid] = np.clip((xy[valid] - origin) / unit, -3, 3) / 3
    bone_mask = valid & valid[PARENTS]
    bones[bone_mask] = np.clip((xy[bone_mask] - xy[PARENTS[bone_mask]]) / unit, -3, 3) / 3
    globals_ = np.array([(box[2] - box[0]) / width, (box[3] - box[1]) / height,
                         float(hips), valid.mean()], np.float32)
    result = np.concatenate((current.ravel(), valid.astype(np.float32), bones.ravel(), bone_mask.astype(np.float32), globals_))
    if result.shape != (64,) or not np.isfinite(result).all():
        raise ValueError('Nonfinite static person features')
    return result.astype(np.float32)


def _load_pose_model(path):
    import os
    path = Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
        raise ValueError('Missing or mismatched official YOLO11n-pose asset: ' + str(path))
    os.environ.setdefault('YOLO_CONFIG_DIR', str(path.resolve().parent / 'settings'))
    import torch
    from ultralytics import YOLO, settings
    settings.update({'sync': False})
    torch.set_num_threads(4)
    return YOLO(str(path))


class StaticPoseFeatureExtractor:
    def __init__(self, model_path=DEFAULT_STATIC_MODEL, window_seconds=.25):
        static_feature_metadata(window_seconds)
        self.detector = _load_pose_model(model_path)
        self.last_timestamp = None
        self.last_keypoints = None
        self.last_valid_mask = None

    def overlay_snapshot(self):
        """Copies of this frame's observed body points, solely for display."""
        return (None if self.last_keypoints is None else self.last_keypoints.copy(),
                None if self.last_valid_mask is None else self.last_valid_mask.copy())

    def update(self, timestamp, frame_bgr, landmarks=None):
        timestamp = float(timestamp)
        if not np.isfinite(timestamp) or (self.last_timestamp is not None and timestamp <= self.last_timestamp):
            raise ValueError('Frame timestamps must be finite and strictly increase')
        frame = np.asarray(frame_bgr)
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8 or min(frame.shape[:2]) < 1:
            raise ValueError('A real uint8 BGR image is required')
        self.last_timestamp = timestamp
        self.last_keypoints = self.last_valid_mask = None
        result = self.detector.predict(frame, imgsz=416, conf=.25, max_det=1, device='cpu', verbose=False)[0]
        if not len(result.boxes):
            return None
        points = result.keypoints.data[0].cpu().numpy()
        row = feature(points, result.boxes.xyxy[0].cpu().numpy(), frame.shape[1], frame.shape[0])
        self.last_keypoints = np.asarray(points, dtype=np.float32).copy()
        self.last_valid_mask = row[20:30].astype(bool)
        return row if row[20:30].any() else None
