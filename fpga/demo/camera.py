"""Local camera pose capture and live FPGA classification.

record saves feature vectors, labels and session IDs, never video. run requires
a separately trained camera model and reports only results returned by FPGA.
"""
import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
import uuid

import numpy as np

from .features import (PoseWindow, append_dataset, DEFAULT_LABELS,
                       feature_metadata, feature_profile_from_metadata, normalize_pose)

DEFAULT_POSE_MODEL = Path('tools/local/camera_demo/pose_landmarker_lite.task')
CONNECTIONS = ((11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),
               (23,25),(25,27),(27,29),(29,31),(24,26),(26,28),(28,30),(30,32))
WINDOW_NAME = 'Camera to FPGA - local processing'
ACTION_ZH = {'standing': '站立', 'left_arm': '左臂抬起', 'right_arm': '右臂抬起',
             'both_arms': '双臂抬起', 'squat': '下蹲', 'lean': '身体侧倾'}


@dataclass(frozen=True)
class CaptureStep:
    phase: str
    emit: bool = False
    remaining: float = 0.0
    discard: bool = False
    windows: int = 0


class CaptureGate:
    """One labelled segment: confirm/wait, prepare, record or retry.

    `valid` means PoseWindow has produced a genuine selected-profile history, never a
    fabricated zero vector. A failed segment stays on the same action; it does
    not count as a completed dataset session.
    """
    def __init__(self, countdown, seconds, interval, *, automatic=False,
                 wait_start=True, timeout=120, min_windows=None):
        if not math.isfinite(countdown) or countdown < 0:
            raise ValueError('Countdown must be finite and nonnegative')
        if not all(math.isfinite(v) and v > 0 for v in (seconds, interval, timeout)):
            raise ValueError('Recording duration, interval and timeout must be positive')
        if automatic and timeout <= countdown + seconds:
            raise ValueError('Pose timeout must exceed countdown plus recording duration')
        maximum = max(1, math.ceil(seconds / interval))
        self.minimum = max(1, math.ceil(maximum / 2)) if min_windows is None else min_windows
        if type(self.minimum) is not int or not 1 <= self.minimum <= maximum:
            raise ValueError('Invalid minimum window count')
        self.countdown, self.seconds, self.interval, self.timeout = countdown, seconds, interval, timeout
        self.entered = self.phase_started = self.last_time = None
        self.last_emit = float('-inf')
        self.phase, self.windows, self.retries = 'waiting', 0, 0
        self.automatic = automatic
        self.start_immediately = not automatic and not wait_start

    def tick(self, now, valid, confirm=False):
        if not math.isfinite(now) or (self.last_time is not None and now < self.last_time):
            raise ValueError('Capture timestamps must be finite and monotonic')
        self.last_time = now
        if self.entered is None:
            self.entered = now
        if self.phase == 'complete':
            return CaptureStep('complete', windows=self.windows)
        if self.automatic and now - self.entered >= self.timeout:
            raise RuntimeError('Automatic capture timed out waiting for enough valid pose samples; '
                               'completed sessions are preserved. Adjust the camera and retry.')
        if self.phase == 'waiting':
            ready = valid if self.automatic else (confirm or self.start_immediately)
            if not ready:
                return CaptureStep('waiting')
            self.start_immediately = False
            self.phase, self.phase_started = 'preparing', now
        if self.phase == 'preparing':
            if self.automatic and not valid:
                self.phase, self.phase_started = 'waiting', None
                return CaptureStep('waiting')
            remaining = self.countdown - (now - self.phase_started)
            if remaining > 0:
                return CaptureStep('preparing', remaining=remaining)
            self.phase, self.phase_started = 'recording', now
        remaining = self.seconds - (now - self.phase_started)
        if remaining <= 0:
            if self.windows >= self.minimum:
                self.phase = 'complete'
                return CaptureStep('complete', windows=self.windows)
            rejected = self.windows
            self.phase, self.phase_started = 'waiting', None
            self.windows, self.last_emit = 0, float('-inf')
            self.retries += 1
            return CaptureStep('retry', discard=True, windows=rejected)
        emit = bool(valid and now - self.last_emit >= self.interval)
        if emit:
            self.windows += 1
            self.last_emit = now
        return CaptureStep('recording', emit=emit, remaining=remaining, windows=self.windows)


class AutoCaptureGate(CaptureGate):
    def __init__(self, countdown, seconds, interval, timeout=120, min_windows=None):
        super().__init__(countdown, seconds, interval, automatic=True,
                         timeout=timeout, min_windows=min_windows)


class ManualCaptureGate(CaptureGate):
    def __init__(self, countdown, seconds, interval, wait_start=True, min_windows=None):
        super().__init__(countdown, seconds, interval, wait_start=wait_start,
                         min_windows=min_windows)


def _chinese_font(width):
    """Optional local font; never download fonts or send camera frames anywhere."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    candidates = (Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc',
                  Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), max(18, min(30, width // 30)))
            except OSError:
                pass
    return None


def _draw_capture_text(frame, english, chinese, font, cv2):
    """Add a header above the preview; never paint over or crop video pixels."""
    if font is None or not chinese:
        header = np.full((12 + 24 * len(english), frame.shape[1], 3), 12, dtype=np.uint8)
        for n, line in enumerate(english):
            cv2.putText(header, line, (8,22+24*n), cv2.FONT_HERSHEY_SIMPLEX,
                        .46, (0,220,255), 1, cv2.LINE_AA)
        return np.concatenate((header, frame), axis=0)
    from PIL import Image, ImageDraw
    line_height = font.size + 9
    image = Image.new('RGB', (frame.shape[1], 12 + line_height * len(chinese)), (12,12,12))
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(chinese):
        draw.text((10, 6+n*line_height), line, font=font,
                  fill=(255,220,40) if n == 0 else (245,245,245))
    header = np.asarray(image)[:, :, ::-1].copy()
    return np.concatenate((header, frame), axis=0)


def _open_camera(args, cv2):
    """Request a real sensor mode; report driver answers without claiming FOV."""
    backend = getattr(args, 'camera_backend', 'auto')
    width, height = getattr(args, 'width', 1280), getattr(args, 'height', 720)
    zoom = getattr(args, 'zoom', None)
    if backend not in ('auto', 'dshow', 'msmf'):
        raise ValueError('Camera backend must be auto, dshow or msmf')
    if any(type(v) is not int or v <= 0 for v in (width, height)):
        raise ValueError('Camera width and height must be positive integers')
    if type(args.camera) is not int or args.camera < 0:
        raise ValueError('Camera index must be a nonnegative integer')
    if zoom is not None and (not math.isfinite(zoom) or zoom <= 0):
        raise ValueError('Camera zoom must be a finite positive native driver value')
    choices = {'dshow': cv2.CAP_DSHOW, 'msmf': cv2.CAP_MSMF}
    requested = [choices[backend]] if backend != 'auto' else (
        [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY])
    cap = None
    for api in requested:
        candidate = cv2.VideoCapture(args.camera, api)
        if candidate.isOpened():
            cap = candidate
            break
        candidate.release()
    if cap is None:
        raise RuntimeError(f'Camera {args.camera} could not be opened with backend {backend}')
    try:
        width_set = bool(cap.set(cv2.CAP_PROP_FRAME_WIDTH, width))
        height_set = bool(cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height))
        zoom_set = bool(cap.set(cv2.CAP_PROP_ZOOM, zoom)) if zoom is not None else None
        def reported(prop):
            value = float(cap.get(prop))
            return value if math.isfinite(value) else None
        info = {'event': 'camera_opened', 'camera': args.camera,
                'backend_requested': backend, 'backend_actual': cap.getBackendName(),
                'width_requested': width, 'height_requested': height,
                'width_set_accepted': width_set, 'height_set_accepted': height_set,
                'width_reported': reported(cv2.CAP_PROP_FRAME_WIDTH),
                'height_reported': reported(cv2.CAP_PROP_FRAME_HEIGHT),
                'fps_reported': reported(cv2.CAP_PROP_FPS),
                'zoom_requested': zoom, 'zoom_set_accepted': zoom_set,
                'zoom_reported': reported(cv2.CAP_PROP_ZOOM),
                'preview_crop': False, 'video_saved': False}
        return cap, info
    except Exception:
        cap.release()
        raise


def read_camera_model(package, *, allow_synthetic_engineering_test=False):
    path = Path(package)/'camera_demo.json'
    if not path.exists():
        raise ValueError('No trained camera_demo.json. Record camera features and run train_camera first; the UCI sensor model cannot classify camera features.')
    model = json.loads(path.read_text(encoding='utf-8'))
    contract = model.get('feature_contract', {})
    if not model.get('trained'):
        raise ValueError('Untrained or incompatible camera model')
    profile = feature_profile_from_metadata(contract)
    source=model.get('dataset_source')
    if source != 'local-camera' and not (allow_synthetic_engineering_test and source == 'synthetic-engineering-test'):
        raise ValueError('Camera inference requires a model trained on labelled local-camera recordings; synthetic/unknown training data are not a human-action model')
    expected = feature_metadata(contract.get('window_seconds', 1.0), profile=profile)
    if any(contract.get(k) != v for k, v in expected.items()):
        raise ValueError('Camera model uses a different feature extraction contract')
    if len(model.get('labels', [])) != 6 or model.get('network') != [64,32,6]:
        raise ValueError('Camera model must define six labels and a 64→32→6 network')
    manifest = json.loads((Path(package)/'manifest.json').read_text(encoding='utf-8'))
    live = manifest.get('live_demo', {})
    if not model.get('package_tag') or model['package_tag'] != live.get('package_tag'):
        raise ValueError('Camera labels/features do not belong to this resident model (package_tag mismatch)')
    if live.get('input_bytes') != 64 or live.get('output_bytes') != 6:
        raise ValueError('Resident dimensions differ from camera classifier')
    if model.get('input_scale') != live.get('input_scale') or model.get('output_scale') != live.get('output_scale'):
        raise ValueError('Camera quantization metadata differs from resident model')
    if model.get('backend_target') != 'int22-raw-v1' or manifest.get('target') != model['backend_target']:
        raise ValueError('Camera model is not compiled for this RAW FPGA backend')
    if model.get('npu_core_starts_per_request',0) < 1 or manifest.get('npu_core_starts',0) < 1:
        raise ValueError('Camera demo package has no real RAW NPU block')
    return model


def _capture_contract(args, model=None):
    """A loaded classifier owns its feature profile; capture chooses explicitly."""
    contract = model['feature_contract'] if model else feature_metadata(
        args.window, profile=getattr(args, 'feature_profile', 'full'))
    return feature_profile_from_metadata(contract), contract


class FPGAWorker:
    """Keep camera timestamps continuous while JTAG handles one request at a time."""
    def __init__(self, package, host, port, timeout, attach=False):
        self.package, self.host, self.port = package, host, port
        self.timeout, self.attach = timeout, attach
        self.pending = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.status, self.result, self.result_at = 'FPGA connecting...', None, None
        self.result_input_at, self.transport = None, None
        self.thread = threading.Thread(target=self._run, daemon=True, name='fpga-jtag-inference')
        self.thread.start()

    def _set(self, status, result=None, input_at=None):
        with self.lock:
            if self.stop.is_set():
                return
            self.status = status
            if result is not None:
                self.result, self.result_at = result, time.monotonic()
                self.result_input_at = input_at

    def _run(self):
        try:
            from .host import DemoClient
            from .transport import OpenOCDTransport
            transport = OpenOCDTransport(self.host, self.port, timeout=self.timeout)
            with self.lock:
                self.transport = transport
            with transport:
                if self.stop.is_set():
                    return
                client = DemoClient.from_package(transport, self.package, timeout=self.timeout)
                self._set('FPGA attaching...' if self.attach else 'FPGA loading model once...')
                client.attach() if self.attach else client.load()
                self._set('FPGA ready')
                while not self.stop.is_set():
                    try:
                        features, captured_at = self.pending.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    self._set('FPGA computing...')
                    result = client.infer(client.quantize(features))
                    if result.backend != 'openocd-jtag':
                        raise RuntimeError('Camera demo requires a real OpenOCD JTAG backend')
                    self._set('FPGA ready', result, captured_at)
        except Exception as e:
            # Clear old results: a communication error must never show a stale
            # result as a prediction for the current image.
            with self.lock:
                if not self.stop.is_set():
                    self.status, self.result, self.result_at = f'FPGA ERROR: {e}', None, None
                    self.result_input_at = None
        finally:
            with self.lock:
                self.transport = None

    def submit(self, features, captured_at=None):
        captured_at = time.monotonic() if captured_at is None else float(captured_at)
        if not math.isfinite(captured_at):
            raise ValueError('Nonfinite camera capture time')
        with self.lock:
            if self.stop.is_set() or not self.status.startswith(('FPGA ready', 'FPGA computing')):
                return
        # One in-flight and one latest window. Drop superseded camera windows.
        try:
            self.pending.put_nowait((features.copy(), captured_at))
        except queue.Full:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                pass
            try:
                self.pending.put_nowait((features.copy(), captured_at))
            except queue.Full:
                pass

    def snapshot(self):
        with self.lock:
            return self.status, self.result, self.result_at, self.result_input_at

    def close(self):
        self.stop.set()
        with self.lock:
            transport = self.transport
        if transport is not None:
            # Closing the socket interrupts an outstanding Tcl read so a quit
            # does not leave a daemon owning the JTAG connection until timeout.
            transport.close()
        self.thread.join(timeout=self.timeout+1)
        if self.thread.is_alive():
            raise RuntimeError('JTAG worker did not stop before its network timeout')


def run_capture(args):
    import cv2
    import mediapipe as mp
    if not args.pose_model.is_file():
        raise ValueError('Missing MediaPipe pose model: ' + str(args.pose_model))
    model = read_camera_model(args.package, allow_synthetic_engineering_test=args.allow_synthetic_engineering_test) if args.command == 'run' else None
    profile, contract = _capture_contract(args, model)
    window_seconds = contract['window_seconds']
    framing = 'head, hands and knees visible; feet not required' if profile == 'knees' else 'full body including feet visible'
    framing_zh = '头、手和膝盖完整入镜（无需脚部）' if profile == 'knees' else '头、手和脚完整入镜'
    if not all(math.isfinite(v) and v > 0 for v in (args.seconds,args.interval)):
        raise ValueError('--seconds and --interval must be positive')
    if args.command == 'record' and (not math.isfinite(args.countdown) or args.countdown < 0):
        raise ValueError('--countdown must be nonnegative')
    if args.command == 'record' and args.wait_start and args.no_display:
        raise ValueError('Space-to-start confirmation requires the camera display')
    automatic = args.command == 'record' and getattr(args, 'auto_advance', False)
    gate = None
    if args.command == 'record':
        gate = AutoCaptureGate(args.countdown, args.seconds, args.interval,
                               getattr(args, 'pose_timeout', 120)) if automatic else ManualCaptureGate(
                                   args.countdown, args.seconds, args.interval, args.wait_start)
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(args.pose_model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1,
        min_pose_detection_confidence=0.5, min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5)
    cap, camera_info = _open_camera(args, cv2)
    camera_info.update(feature_profile=profile, feature_schema=contract['schema'])
    print(json.dumps(camera_info), flush=True)
    worker = None
    samples, timestamps = [], []
    start, last_emit, last_ms = time.monotonic(), float('-inf'), -1
    capture_start = start
    confirm_record = False
    cancelled, last_result_seq, last_error = False, None, None
    font, font_checked = None, False
    window = PoseWindow(window_seconds)
    session = args.session or f'{args.label}-{uuid.uuid4().hex[:12]}' if args.command == 'record' else None
    try:
        if model:
            worker = FPGAWorker(args.package, args.host, args.port, args.timeout, args.attach)
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError('Camera frame read failed')
                if last_ms < 0:
                    print(json.dumps({'event': 'camera_first_frame', 'width_actual': frame.shape[1],
                                      'height_actual': frame.shape[0],
                                      'preview_crop': False}), flush=True)
                now = time.monotonic(); elapsed = now-start
                # MediaPipe's video timestamp remains monotonic when a guided
                # record resets its separate preparation/record countdown.
                ms = max(last_ms+1, int((now-capture_start)*1000)); last_ms = ms
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detection = detector.detect_for_video(image, ms)
                landmarks = None
                if detection.pose_landmarks:
                    landmarks = np.array([[p.x,p.y,p.z,p.visibility] for p in detection.pose_landmarks[0]])
                pose = normalize_pose(landmarks, frame.shape[1], frame.shape[0], profile=profile) if landmarks is not None else None
                features = window.update(now, pose)
                pose_status = 'Pose ready' if features is not None else f'Need {framing} / {window_seconds:g}s history'
                lines = [f'{args.command.upper()} - {pose_status}']
                chinese = []
                if args.command == 'record':
                    action = ACTION_ZH.get(args.label, args.label)
                    chinese = [getattr(args, 'progress_zh', f'当前动作：{action}')]
                    step = gate.tick(now, features is not None, confirm=confirm_record)
                    confirm_record = False
                    if step.discard:
                        samples.clear(); timestamps.clear()
                        window = PoseWindow(window_seconds)
                        print(json.dumps({'event': 'segment_retry', 'label': args.label,
                                          'discarded_windows': step.windows,
                                          'minimum_windows': gate.minimum,
                                          'manual_confirmation_required': not automatic}), flush=True)
                        if args.no_display and not automatic:
                            raise RuntimeError('Too few valid pose samples; retry with the camera display')
                    if step.emit:
                        samples.append(features.copy()); timestamps.append(now)
                    if step.phase == 'complete':
                        break
                    if step.phase in ('waiting', 'retry'):
                        if automatic:
                            lines.append(f'AUTO: {framing}; {args.label}; Q: stop')
                            chinese.append(f'等待稳定姿态：{framing_zh}')
                        else:
                            lines.append(f'WAITING: {args.label}. SPACE: confirm and begin; Q: stop')
                            lines.append(getattr(args,'progress','Move to the labelled pose before confirming'))
                            chinese.append('尚未开始：点击画面，再按空格开始本动作')
                            chinese.append(f'姿态已稳定：{framing_zh}' if features is not None else f'请调整位置：{framing_zh}')
                    elif step.phase == 'preparing':
                        lines.append(f'PREPARE {step.remaining:.1f}s: {args.label}')
                        chinese.append(f'准备动作，倒计时 {step.remaining:.1f} 秒')
                    else:
                        lines.append(f'RECORD {args.label}: {step.windows} windows; {step.remaining:.1f}s')
                        chinese.append(f'正在录制：{step.windows} 个窗口，剩余 {step.remaining:.1f} 秒')
                        if features is None:
                            chinese.append(f'未看清所需关键点，本帧不采样：{framing_zh}')
                    if gate.retries:
                        lines.append(f'Too few valid windows; same action retry {gate.retries}')
                        if automatic:
                            chinese.append(f'采样不足，当前动作重试 {gate.retries} 次')
                        else:
                            chinese.append('采样不足，仍是当前动作；调整后按空格重试')
                    if automatic:
                        chinese.append('自动切换动作，无需按空格；Q 退出')
                    lines.append('Saving features only, no video. Q: finish')
                    chinese.append('只保存姿态特征，不保存视频')
                else:
                    if features is not None and now-last_emit >= args.interval:
                        worker.submit(features, now); last_emit = now
                    status, result, at, input_at = worker.snapshot(); lines.append(status)
                    if status.startswith('FPGA ERROR') and status != last_error:
                        print(json.dumps({'event':'fpga_error','message':status}),flush=True);last_error=status
                    if result is not None:
                        age = now-input_at
                        label = model['labels'][result.class_id] if 0 <= result.class_id < len(model['labels']) else 'INVALID CLASS'
                        if age < max(1,window_seconds+2*args.interval):
                            lines.append(f'Last FPGA result: {label}, seq={result.sequence}, input age={age:.1f}s')
                            lines.append(f'JTAG roundtrip={result.roundtrip_ms:.0f}ms; device cycles={result.cycles}')
                        else:
                            lines.append(f'Old FPGA input ({age:.1f}s): {label}; waiting for a fresh result')
                        if features is None:
                            lines.append('No current pose prediction; previous FPGA result shown only as history')
                        if result.sequence != last_result_seq:
                            print(json.dumps({'event':'fpga_result','sequence':result.sequence,
                                              'label':label,'class_id':result.class_id,
                                              'scores':list(result.scores),'device_cycles':result.cycles,
                                              'roundtrip_ms':result.roundtrip_ms,'input_age_ms':1000*age,
                                              'backend':result.backend}),flush=True)
                            last_result_seq=result.sequence
                    if model.get('dataset_source') != 'local-camera':
                        lines.insert(0,'SYNTHETIC ENGINEERING TEST ONLY - NO HUMAN ACCURACY')
                    lines.append('PC: pose; FPGA RAW NPU: FC1; FPGA CPU: FC2/ReLU. Q: exit')
                    if elapsed >= args.seconds:
                        break
                if landmarks is not None:
                    for a,b in CONNECTIONS:
                        if profile == 'knees' and (a not in contract['joints'] or b not in contract['joints']):
                            continue
                        if landmarks[a,3] >= .5 and landmarks[b,3] >= .5:
                            pa = tuple((landmarks[a,:2]*[frame.shape[1],frame.shape[0]]).astype(int))
                            pb = tuple((landmarks[b,:2]*[frame.shape[1],frame.shape[0]]).astype(int))
                            cv2.line(frame,pa,pb,(80,220,80),2)
                # Display may be mirrored for convenience, features above never are.
                frame = cv2.flip(frame, 1)
                if not font_checked:
                    font = _chinese_font(frame.shape[1]) if chinese else None
                    font_checked = True
                    if not args.no_display:
                        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(WINDOW_NAME, 800, 600)
                frame = _draw_capture_text(frame, lines, chinese, font, cv2)
                if not args.no_display:
                    cv2.imshow(WINDOW_NAME, frame)
                    key = cv2.waitKey(1)&0xff
                    if key in (ord('q'),27):
                        cancelled=True
                        break
                    if args.command == 'record' and not automatic and gate.phase == 'waiting' and key == ord(' '):
                        confirm_record = True
                        window=PoseWindow(window_seconds)
    finally:
        cap.release()
        if not args.no_display:
            cv2.destroyAllWindows()
        if worker:
            worker.close()
    if args.command == 'record':
        if automatic and cancelled:
            # Completed prior segments are already saved. An interrupted auto
            # segment must not create a tiny or unqualified training session.
            return False
        if cancelled and len(samples) < gate.minimum:
            return False
        metadata = feature_metadata(window_seconds, profile=profile); metadata['capture_source'] = 'local-camera'
        total = append_dataset(args.output, samples, args.label, session, timestamps, metadata)
        print(json.dumps({'dataset': str(args.output), 'label': args.label, 'session': session,
                          'new_windows': len(samples), 'total_windows': total, 'video_saved': False}, indent=2))
    return not cancelled


def collect(args):
    """Guided sessions, with manual confirmation or pose-gated auto countdown."""
    if args.rounds < 3 or len(set(args.labels)) != 6:
        raise ValueError('Collect at least three rounds of six distinct labels for session holdout')
    if args.no_display:
        raise ValueError('Guided collection requires a display for action instructions')
    automatic = getattr(args, 'auto_advance', False)
    for round_id in range(1,args.rounds+1):
        for index,label in enumerate(args.labels):
            options=vars(args).copy()
            options.update(command='record',label=label,wait_start=not automatic,
                           session=f'r{round_id}-{label}-{uuid.uuid4().hex[:12]}',
                           progress=f'Round {round_id}/{args.rounds}, class {index+1}/6: {label}',
                           progress_zh=f'第 {round_id}/{args.rounds} 轮，动作 {index+1}/6：{ACTION_ZH.get(label, label)}')
            instruction = 'Valid selected-profile pose starts countdown automatically.' if automatic else 'Take position, then SPACE in camera window.'
            print(f'Round {round_id}/{args.rounds}: {label}. {instruction}',flush=True)
            if not run_capture(argparse.Namespace(**options)):
                return False
    print(json.dumps({'event':'collection_complete','dataset':str(args.output),
                      'labels':args.labels,'rounds':args.rounds,
                      'feature_profile':getattr(args,'feature_profile','full'),'video_saved':False}),flush=True)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    for name in ('record','collect','run'):
        c = commands.add_parser(name)
        c.add_argument('--camera',type=int,default=0)
        c.add_argument('--camera-backend',choices=('auto','dshow','msmf'),default='auto',
                       help='Windows auto prefers DirectShow; explicit backends do not silently fall back')
        c.add_argument('--width',type=int,default=1280,help='Requested real camera width; actual mode is logged')
        c.add_argument('--height',type=int,default=720,help='Requested real camera height; actual mode is logged')
        c.add_argument('--zoom',type=float,default=None,
                       help='Optional native driver zoom value; no synthetic wide-angle or digital crop')
        c.add_argument('--pose-model',type=Path,default=DEFAULT_POSE_MODEL)
        c.add_argument('--seconds',type=float,default=15 if name=='record' else 10 if name=='collect' else 3600)
        c.add_argument('--interval',type=float,default=.25)
        c.add_argument('--no-display',action='store_true')
        if name in ('record','collect'):
            c.add_argument('--feature-profile',choices=('full','knees'),default='full',
                           help='Versioned capture features: full requires feet; knees requires head/hands/knees only')
            if name == 'record':
                c.add_argument('--label',required=True)
                c.add_argument('--session',default='')
                c.add_argument('--wait-start',action='store_true')
            else:
                c.add_argument('--labels',nargs=6,default=DEFAULT_LABELS)
                c.add_argument('--rounds',type=int,default=3)
                c.add_argument('--auto-advance',action='store_true',
                               help='Valid selected-profile pose starts each countdown; switch actions automatically')
                c.add_argument('--pose-timeout',type=float,default=120,
                               help='Maximum total seconds to obtain a qualified segment for each action')
            c.add_argument('--output',type=Path,required=True)
            c.add_argument('--window',type=float,default=1)
            c.add_argument('--countdown',type=float,default=3)
        else:
            c.add_argument('--package',type=Path,required=True)
            c.add_argument('--host',default='127.0.0.1')
            c.add_argument('--port',type=int,default=6666)
            c.add_argument('--timeout',type=float,default=10)
            c.add_argument('--attach',action='store_true')
            c.add_argument('--allow-synthetic-engineering-test',action='store_true',
                           help='Explicit engineering override; never a human-action accuracy demonstration')
    args = p.parse_args()
    try:
        if args.command == 'collect':
            if not collect(args):
                p.exit(130,'Collection stopped; completed feature sessions are saved locally.\n')
        else:
            run_capture(args)
    except (ValueError, RuntimeError, ImportError, OSError) as e:
        p.exit(2, f'Camera demo stopped: {e}\n')


if __name__ == '__main__':
    main()
