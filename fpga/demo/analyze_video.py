"""Analyze labelled local videos without requiring a complete detected skeleton.

Raw recordings and frame-clock sidecars are immutable inputs. Every decoded
frame contributes to temporal history, including frames with no detected pose.
Only time-based subsampling is applied, never a pose-visibility filter.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .video_features import VIDEO_JOINTS, VideoFeatureExtractor, video_feature_metadata

DEFAULT_POSE_MODEL = Path('tools/local/camera_demo/pose_landmarker_lite.task')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, contents):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(contents, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def _relative_source(directory, name):
    _require(isinstance(name, str) and name, 'Missing relative video or timestamp path')
    source = (directory / name).resolve()
    _require(not Path(name).is_absolute() and source.is_relative_to(directory.resolve()),
             'Video and timestamp paths must remain inside the recording directory')
    _require(source.is_file(), 'Recorded source is missing: ' + name)
    return source


def read_frame_timestamps(path, expected_count):
    entries = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    _require(len(entries) == expected_count and expected_count > 0, 'Timestamp count differs from recorded frame count')
    timestamps = []
    for index, entry in enumerate(entries):
        stamp = entry.get('monotonic_seconds')
        _require(type(entry.get('frame_index')) is int and entry['frame_index'] == index,
                 'Frame timestamp indices must be contiguous from zero')
        _require(isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and math.isfinite(stamp),
                 'Every recorded frame needs an actual finite timestamp')
        _require(not timestamps or stamp > timestamps[-1], 'Frame timestamps must strictly increase')
        timestamps.append(float(stamp))
    return np.array(timestamps, dtype=np.float64)


def analyze_frames(frames, timestamps, detect_landmarks, *, interval=.25, window_seconds=1.0):
    """Testable shared offline loop; detector(frame, relative_ms) may return None."""
    _require(math.isfinite(interval) and interval > 0, 'Sample interval must be finite and positive')
    stamps = np.asarray(timestamps, dtype=np.float64)
    _require(stamps.ndim == 1 and len(stamps) > 0 and np.isfinite(stamps).all() and (np.diff(stamps) > 0).all(),
             'Expected actual strictly increasing frame timestamps')
    extractor = VideoFeatureExtractor(window_seconds=window_seconds)
    iterator = iter(frames)
    samples, sampled_times = [], []
    joint_counts = np.zeros(len(VIDEO_JOINTS), dtype=np.int64)
    detected, any_joint, all_joints, no_joint_samples, all_zero_samples = 0, 0, 0, 0, 0
    next_sample, last_ms = float(stamps[0]), -1
    for index, timestamp in enumerate(stamps):
        try:
            frame = next(iterator)
        except StopIteration as error:
            raise ValueError('Video decoded fewer frames than its actual timestamp sidecar') from error
        milliseconds = max(last_ms + 1, int((timestamp - stamps[0]) * 1000))
        last_ms = milliseconds
        landmarks = detect_landmarks(frame, milliseconds)
        feature = extractor.update(timestamp, frame, landmarks)
        mask = extractor.last_observation_mask.astype(bool)
        detected += int(landmarks is not None)
        any_joint += int(mask.any())
        all_joints += int(mask.all())
        joint_counts += mask
        if timestamp + 1e-9 >= next_sample:
            samples.append(feature)
            sampled_times.append(timestamp)
            no_joint_samples += int(not mask.any())
            all_zero_samples += int(not feature.any())
            next_sample += (math.floor(max(0, timestamp - next_sample) / interval) + 1) * interval
    try:
        next(iterator)
    except StopIteration:
        pass
    else:
        raise ValueError('Video decoded more frames than its actual timestamp sidecar')
    coverage = {
        'frames_decoded': len(stamps), 'pose_detection_frames': detected,
        'frames_any_observed_joint': any_joint, 'frames_all_ten_observed': all_joints,
        'mean_selected_joint_coverage': float(joint_counts.sum() / (len(stamps) * len(VIDEO_JOINTS))),
        'joint_observed_frames': {str(joint): int(count) for joint, count in zip(VIDEO_JOINTS, joint_counts)},
        'samples': len(samples), 'samples_with_no_observed_joints': no_joint_samples,
        'all_zero_feature_samples': all_zero_samples,
        'first_frame_timestamp': float(stamps[0]), 'last_frame_timestamp': float(stamps[-1]),
        'clock_source': 'recorded per-frame monotonic_seconds; nominal encoder fps is not used',
        'pose_coverage_is_diagnostic_only': True,
    }
    return np.stack(samples).astype(np.float32), np.array(sampled_times, dtype=np.float64), coverage


class _PoseDetector:
    def __init__(self, model_path):
        import cv2
        import mediapipe as mp
        self.cv2, self.mp = cv2, mp
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1,
            min_pose_detection_confidence=.5, min_pose_presence_confidence=.5, min_tracking_confidence=.5)
        self.detector = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.detector.close()

    def __call__(self, frame, milliseconds):
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                              data=self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB))
        result = self.detector.detect_for_video(image, milliseconds)
        if not result.pose_landmarks:
            return None
        return np.array([[p.x, p.y, p.z, p.visibility] for p in result.pose_landmarks[0]], dtype=np.float32)


def _video_frames(path):
    import cv2
    capture = cv2.VideoCapture(str(path))
    _require(capture.isOpened(), 'Could not open recorded video: ' + str(path))
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            yield frame
    finally:
        capture.release()


def analyze_manifest(manifest_path, output_path, *, report_path=None, pose_model=DEFAULT_POSE_MODEL,
                     interval=.25, window_seconds=1.0, detector_factory=None, video_frames=None):
    manifest_path, output_path = Path(manifest_path).resolve(), Path(output_path).resolve()
    report_path = Path(report_path).resolve() if report_path else output_path.with_suffix('.report.json')
    _require(output_path != report_path, 'Dataset and report must use different paths')
    _require(not output_path.exists() and not report_path.exists(), 'Dataset and report paths must be new; existing data are preserved')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    _require(manifest.get('format') == 'camera_video_sessions_v1', 'Unsupported raw-video manifest')
    labels = manifest.get('labels', [])
    _require(len(labels) == 6 and len(set(labels)) == 6 and all(isinstance(label, str) and label for label in labels),
             'Manifest must define six distinct labelled actions')
    clips = manifest.get('clips', [])
    _require(isinstance(clips, list) and clips, 'Manifest has no recorded clips')
    _require(math.isfinite(interval) and interval > 0, 'Sample interval must be finite and positive')
    if detector_factory is None:
        _require(Path(pose_model).is_file(), 'Missing MediaPipe pose model: ' + str(pose_model))
        detector_factory = lambda: _PoseDetector(pose_model)
    video_frames = video_frames or _video_frames
    all_features, all_timestamps, all_labels, all_sessions = [], [], [], []
    reports, sources, seen_sessions = [], [], set()
    for clip in clips:
        label, session = clip.get('label'), clip.get('session')
        _require(label in labels and isinstance(session, str) and session and session not in seen_sessions,
                 'Clips need a known label and distinct independent session IDs')
        seen_sessions.add(session)
        included = clip.get('complete') is True and clip.get('status') == 'complete'
        frame_count = clip.get('frame_count')
        _require(type(frame_count) is int and frame_count >= 0, 'Manifest must record actual nonnegative frame_count')
        if not included and frame_count == 0:
            reports.append({'label': label, 'session': session, 'path': clip.get('path'),
                            'included_in_dataset': False, 'frames_decoded': 0,
                            'reason': 'Empty partial clip preserved; no recorded frames to analyze'})
            continue
        video = _relative_source(manifest_path.parent, clip.get('path'))
        clock = _relative_source(manifest_path.parent, clip.get('timestamps_path'))
        timestamps = read_frame_timestamps(clock, clip['frame_count'])
        frames = video_frames(video)
        try:
            with detector_factory() as detector:
                features, times, coverage = analyze_frames(frames, timestamps, detector, interval=interval, window_seconds=window_seconds)
        finally:
            close = getattr(frames, 'close', None)
            if close is not None:
                close()
        source = {'path': str(video), 'sha256': _digest(video), 'timestamps_path': str(clock),
                  'timestamps_sha256': _digest(clock), 'label': label, 'session': session}
        if included:
            all_features.append(features)
            all_timestamps.append(times)
            all_labels.extend([label] * len(features))
            all_sessions.extend([session] * len(features))
            sources.append(source)
        reports.append({**source, 'included_in_dataset': included, 'training_samples': len(features) if included else 0,
                        'reason': 'Completed independent session' if included else 'Partial clip analyzed diagnostically; excluded from training',
                        **coverage})
    counts = Counter(all_labels)
    session_counts = {label: len({session for item_label, session in zip(all_labels, all_sessions) if item_label == label}) for label in labels}
    ready = all(counts[label] >= 12 and session_counts[label] >= 3 for label in labels)
    report = {'format': 'camera_video_analysis_v1', 'source_manifest': str(manifest_path),
              'source_manifest_sha256': _digest(manifest_path), 'feature_schema': video_feature_metadata(window_seconds)['schema'],
              'labels': labels, 'sample_interval_seconds': interval, 'clips': reports,
              'class_samples': dict(counts), 'class_independent_sessions': session_counts,
              'independent_holdouts_ready': ready, 'dataset_written': False, 'hardware_verified': False,
              'coverage_scope': 'Pose visibility is diagnostic only; all-zero masks remain in the dataset with actual image features',
              'accuracy_scope': 'No classification accuracy is established by video extraction; train/test must separate entire sessions',
              'raw_videos_preserved': True}
    _write_json(report_path, report)
    _require(ready, 'Need at least 12 samples and three completed independent sessions per action; videos/report are preserved')
    metadata = video_feature_metadata(window_seconds)
    metadata.update(capture_source='local-camera', source_video_manifest=str(manifest_path),
                    source_video_manifest_sha256=_digest(manifest_path), source_videos=sources,
                    sample_interval_seconds=float(interval), video_analysis_report=str(report_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + '.tmp.npz')
    _require(not temporary.exists(), 'Refusing to overwrite an existing temporary dataset')
    np.savez_compressed(temporary, features=np.concatenate(all_features), labels=np.array(all_labels),
                        sessions=np.array(all_sessions), timestamps=np.concatenate(all_timestamps),
                        metadata=np.array(json.dumps(metadata, sort_keys=True)))
    temporary.replace(output_path)
    report.update(dataset_written=True, dataset=str(output_path), dataset_sha256=_digest(output_path),
                  total_samples=len(all_labels))
    _write_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--pose-model', type=Path, default=DEFAULT_POSE_MODEL)
    parser.add_argument('--interval', type=float, default=.25)
    parser.add_argument('--window', type=float, default=1.0)
    args = parser.parse_args()
    try:
        report = analyze_manifest(args.manifest, args.output, report_path=args.report,
                                  pose_model=args.pose_model, interval=args.interval, window_seconds=args.window)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(2, f'Video analysis failed: {error}\n')
    print(json.dumps({'dataset': report['dataset'], 'report': str(args.report or args.output.with_suffix('.report.json')),
                      'samples': report['total_samples'], 'class_samples': report['class_samples'],
                      'class_independent_sessions': report['class_independent_sessions'],
                      'feature_schema': report['feature_schema'], 'hardware_verified': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
