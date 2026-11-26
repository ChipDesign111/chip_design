"""Display the observed COCO body joints without changing inference inputs."""

import cv2
import numpy as np


_GREEN = (80, 220, 80)
_BONES = ((5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
          (5, 11), (6, 12), (11, 12), (11, 13), (12, 14))


def draw_static_pose(frame_bgr, keypoints, valid_mask=None):
    """Return a BGR copy with only valid shoulders, arms, hips and knees drawn.

    ``keypoints`` are original-image COCO17 xy/confidence coordinates. A supplied
    ten-joint mask corresponds to indices 5..14 and can only hide observations;
    confidence, finite values and the same 4% frame margin are always checked.
    """
    frame = np.asarray(frame_bgr)
    if (frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8 or
            min(frame.shape[:2]) < 1):
        raise ValueError('A uint8 BGR image is required')
    result = frame.copy()
    if keypoints is None:
        return result

    points = np.asarray(keypoints, dtype=np.float64)
    if points.shape != (17, 3):
        raise ValueError('Expected COCO17 pixel xy/confidence coordinates')
    height, width = frame.shape[:2]
    body = points[5:15]
    xy = body[:, :2]
    valid = (np.isfinite(body).all(axis=1) & (body[:, 2] >= .25) &
             (xy[:, 0] >= width * .04) & (xy[:, 0] <= width * .96) &
             (xy[:, 1] >= height * .04) & (xy[:, 1] <= height * .96))
    if valid_mask is not None:
        mask = np.asarray(valid_mask, dtype=bool)
        if mask.shape != (10,):
            raise ValueError('Expected a ten-joint mask for COCO indices 5..14')
        valid &= mask

    # Convert only safe points: NaNs and large out-of-frame values never reach cv2.
    pixels = {index + 5: tuple(np.rint(xy[index]).astype(int))
              for index in np.flatnonzero(valid)}
    for start, end in _BONES:
        if start in pixels and end in pixels:
            cv2.line(result, pixels[start], pixels[end], _GREEN, 2, cv2.LINE_AA)
    for point in pixels.values():
        cv2.circle(result, point, 3, _GREEN, -1, cv2.LINE_AA)
    return result
