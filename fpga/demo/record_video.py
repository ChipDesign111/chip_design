"""Manual clean-video collection; analysis and pose detection happen offline.

SPACE starts and ENTER stops one labelled clip. Q, Escape or closing the window preserves
an active clip as partial. Frames are encoded before any preview/header work.
There is no landmark visibility gate, detector, audio stream or video upload.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

import numpy as np

from .camera import ACTION_ZH, _chinese_font, _draw_capture_text, _open_camera
from .features import DEFAULT_LABELS

WINDOW_NAME = 'Camera raw video recording'
MANIFEST_FORMAT = 'camera_video_sessions_v1'


class VideoSessionRecorder:
    """Disk-backed clip controller, independent of the camera and GUI."""
    def __init__(self, output_dir, labels, rounds, width, height, fps, writer_factory,
                 camera_info=None):
        if (len(labels) != 6 or len(set(labels)) != 6 or
                any(not isinstance(label, str) or not label for label in labels)):
            raise ValueError('Provide six distinct nonempty action labels')
        if type(rounds) is not int or rounds < 1:
            raise ValueError('Rounds must be a positive integer')
        if any(type(v) is not int or v <= 0 for v in (width, height)):
            raise ValueError('Video dimensions must be positive integers')
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('Encoder FPS must be a finite positive nominal rate')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.labels, self.rounds = tuple(labels), rounds
        self.width, self.height, self.fps = width, height, float(fps)
        self.writer_factory = writer_factory
        self.plan = [(round_id, index, label) for round_id in range(1, rounds+1)
                     for index, label in enumerate(labels)]
        self.position, self.active = 0, None
        self.writer = self.timestamps = None
        self.last_frame_time, self.last_checkpoint = None, float('-inf')
        self.closed = False
        self.manifest = {'format': MANIFEST_FORMAT, 'labels': list(labels), 'rounds': rounds,
                         'status': 'waiting', 'camera': camera_info or {}, 'clips': [],
                         'codec': 'MJPG', 'container': 'AVI', 'audio_saved': False,
                         'clean_frames_before_preview': True, 'preview_mirrored': True,
                         'timestamp_source': 'time.monotonic at frame-read completion',
                         'fps_is_nominal': True, 'completed_clips': 0}
        self._checkpoint()

    @property
    def finished(self):
        return self.position == len(self.plan)

    @property
    def current_action(self):
        return None if self.finished else self.plan[self.position]

    def _checkpoint(self):
        temporary = self.output_dir / '.manifest.json.tmp'
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(self.manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(self.output_dir / 'manifest.json')

    def _validate_frame(self, frame):
        if (not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or
                frame.shape != (self.height, self.width, 3)):
            raise ValueError(f'Camera frame changed size/type; expected {self.width}x{self.height} BGR uint8')

    def toggle(self, frame, timestamp):
        if self.closed or self.finished:
            raise RuntimeError('Recording session has ended')
        if self.active is not None:
            return self._finalize(True, 'space', timestamp)
        self._validate_frame(frame)
        if not math.isfinite(timestamp):
            raise ValueError('Frame timestamp must be finite')
        round_id, index, label = self.current_action
        safe_label = re.sub(r'[^A-Za-z0-9_-]', '_', label)[:40] or 'action'
        session = f'r{round_id}-{safe_label}-{uuid.uuid4().hex[:12]}'
        path, timestamps_path = f'{session}.avi', f'{session}.frames.jsonl'
        video_path = self.output_dir / path
        if video_path.exists():
            raise FileExistsError(video_path)
        clip = {'path': path, 'timestamps_path': timestamps_path, 'label': label,
                'session': session, 'round': round_id, 'class_index': index,
                'width': self.width, 'height': self.height, 'fps': self.fps,
                'fps_is_nominal': True, 'frame_count': 0, 'started_monotonic': timestamp,
                'last_frame_monotonic': None, 'duration_seconds': 0.0,
                'observed_fps': None, 'complete': False, 'status': 'recording',
                'audio_saved': False, 'preview_overlay_saved': False}
        self.manifest['clips'].append(clip)
        self.active = clip
        self.manifest['status'] = 'recording'
        try:
            self.writer = self.writer_factory(video_path, self.fps, (self.width, self.height))
            if not self.writer.isOpened():
                raise RuntimeError('MJPG video writer could not open: ' + str(video_path))
            self.timestamps = (self.output_dir / timestamps_path).open('x', encoding='utf-8')
            self.append(frame, timestamp)
        except Exception as error:
            self.interrupt('writer_error', str(error))
            raise
        return clip

    def append(self, frame, timestamp):
        if self.active is None:
            return False
        self._validate_frame(frame)
        if not math.isfinite(timestamp) or (self.last_frame_time is not None and timestamp <= self.last_frame_time):
            raise ValueError('Frame timestamps must be finite and strictly increasing')
        if not self.writer.isOpened():
            raise RuntimeError('Video writer closed unexpectedly')
        result = self.writer.write(frame)
        if result is False or not self.writer.isOpened():
            raise RuntimeError('Video writer rejected a camera frame')
        clip = self.active
        stamp = {'frame_index': clip['frame_count'], 'monotonic_seconds': timestamp,
                 'relative_seconds': timestamp - clip['started_monotonic']}
        self.timestamps.write(json.dumps(stamp, allow_nan=False)+'\n')
        self.timestamps.flush()
        clip['frame_count'] += 1
        clip['last_frame_monotonic'] = timestamp
        clip['duration_seconds'] = stamp['relative_seconds']
        if clip['duration_seconds'] > 0:
            clip['observed_fps'] = (clip['frame_count']-1) / clip['duration_seconds']
        self.last_frame_time = timestamp
        if clip['frame_count'] == 1 or timestamp - self.last_checkpoint >= 1:
            self._checkpoint(); self.last_checkpoint = timestamp
        return True

    def _finalize(self, complete, reason, timestamp, error=None):
        clip = self.active
        release_error = None
        try:
            if self.writer is not None:
                self.writer.release()
        except Exception as failure:
            release_error = str(failure)
        finally:
            if self.timestamps is not None:
                self.timestamps.flush(); os.fsync(self.timestamps.fileno()); self.timestamps.close()
            self.writer = self.timestamps = None
        video = self.output_dir / clip['path']
        if not clip['frame_count'] or not video.is_file() or video.stat().st_size == 0:
            error = error or 'Encoder produced no video frames/file bytes'
        error = error or release_error
        clip.update(complete=bool(complete and not error), ended_by=reason,
                    ended_monotonic=timestamp,
                    wall_duration_seconds=max(0.0, timestamp-clip['started_monotonic']),
                    status='failed' if error else 'complete' if complete else 'partial')
        if error:
            clip['error'] = error
        self.active = None
        if clip['complete']:
            self.position += 1
            self.manifest['completed_clips'] = self.position
            self.manifest['status'] = 'complete' if self.finished else 'waiting'
        else:
            self.manifest['status'] = 'error' if error else 'interrupted'
        self._checkpoint()
        if complete and error:
            raise RuntimeError(error)
        return clip

    def interrupt(self, reason='q', error=None):
        clip = self._finalize(False, reason, time.monotonic(), error) if self.active else None
        if not self.finished:
            self.manifest['status'] = 'error' if error else 'interrupted'
            if error:
                self.manifest['error'] = error
            self._checkpoint()
        self.closed = True
        return clip


def run(args):
    import cv2
    if args.output_dir.exists():
        raise FileExistsError('Use a fresh output directory; existing videos will not be overwritten')
    cap, info = _open_camera(args, cv2)
    recorder = None
    try:
        ok, frame = cap.read(); timestamp = time.monotonic()
        if not ok or frame is None:
            raise RuntimeError('Camera frame read failed before recording')
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise RuntimeError('Camera must provide BGR uint8 frames')
        height, width = frame.shape[:2]
        reported_fps = info.get('fps_reported')
        fps = reported_fps if reported_fps and reported_fps > 0 else 30.0
        info.update(width_actual=width, height_actual=height, video_saved=True,
                    audio_saved=False, pose_gating=False,
                    encoder_nominal_fps=fps, encoder_fps_source='camera_reported' if reported_fps and reported_fps > 0 else 'fallback_30')
        print(json.dumps(info), flush=True)
        factory = lambda path, rate, size: cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), rate, size)
        recorder = VideoSessionRecorder(args.output_dir, args.labels, args.rounds, width, height, fps, factory, info)
        font = _chinese_font(width)
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, 960, 720)
        while True:
            recorder.append(frame, timestamp)
            round_id, index, label = recorder.current_action
            action = ACTION_ZH.get(label, label)
            chinese = [f'第 {round_id}/{args.rounds} 轮，动作 {index+1}/6：{action}']
            english = [f'Round {round_id}/{args.rounds}, action {index+1}/6: {label}']
            if recorder.active:
                clip = recorder.active
                chinese += [f'正在录制 REC：{clip["duration_seconds"]:.1f} 秒，已写入 {clip["frame_count"]} 帧',
                            '按回车保存本段并切换；Q 退出并保留当前片段']
                english += [f'REC {clip["duration_seconds"]:.1f}s / {clip["frame_count"]} frames; ENTER save; Q finish partial']
            else:
                chinese += ['尚未录制：点击画面，按空格开始当前动作',
                            f'已完成 {recorder.position}/{len(recorder.plan)} 段；Q 退出']
                english += [f'SPACE starts clip; saved {recorder.position}/{len(recorder.plan)} clips; Q exit']
            chinese.append('无需完整入镜；保存原始视频，不录声音')
            english.append('No pose gate. Clean video only; no audio.')
            preview = _draw_capture_text(cv2.flip(frame,1), english, chinese, font, cv2)
            cv2.imshow(WINDOW_NAME, preview)
            key = cv2.waitKey(1) & 0xff
            try:
                closed = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1
            except cv2.error:
                closed = True
            if key in (ord('q'),27) or closed:
                clip = recorder.interrupt('window_close' if closed else 'q')
                print(json.dumps({'event':'recording_interrupted','saved_clips':len(recorder.manifest['clips']),
                                  'completed_clips':recorder.position,
                                  'partial_frames':clip['frame_count'] if clip else 0}),flush=True)
                return 130
            # Different start/stop keys prevent OS key-repeat from turning one
            # held SPACE into an unintended sub-second completed recording.
            if (key == ord(' ') and recorder.active is None) or (key in (10,13) and recorder.active is not None):
                started = recorder.active is None
                clip = recorder.toggle(frame, timestamp)
                print(json.dumps({'event':'clip_started' if started else 'clip_saved',
                                  'label':clip['label'],'session':clip['session'],
                                  'frame_count':clip['frame_count'],'complete':clip['complete'],
                                  'path':clip['path']}),flush=True)
                if recorder.finished:
                    print(json.dumps({'event':'video_collection_complete','completed_clips':recorder.position,
                                      'manifest':str(args.output_dir/'manifest.json')}),flush=True)
                    return 0
            ok, frame = cap.read(); timestamp = time.monotonic()
            if not ok or frame is None:
                raise RuntimeError('Camera frame read failed; captured clips are retained')
    except BaseException as error:
        if recorder is not None and not recorder.closed:
            recorder.interrupt('keyboard_interrupt' if isinstance(error,KeyboardInterrupt) else 'error',
                               None if isinstance(error,KeyboardInterrupt) else str(error))
        raise
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--labels',nargs=6,default=DEFAULT_LABELS)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--camera-backend',choices=('auto','dshow','msmf'),default='auto')
    parser.add_argument('--width',type=int,default=1280)
    parser.add_argument('--height',type=int,default=720)
    parser.add_argument('--zoom',type=float,default=None)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        return 130
    except (ValueError,RuntimeError,OSError) as error:
        parser.exit(2,f'Video recording stopped: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
