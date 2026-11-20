"""Recorder transitions and durable metadata using synthetic frames/fake encoder.

These tests never open a camera or GUI and do not claim real codec validation.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.record_video import DEFAULT_LABELS, MANIFEST_FORMAT, VideoSessionRecorder, run


class FakeWriter:
    def __init__(self, path, fps, size, *, opened=True, empty_output=False):
        self.path, self.fps, self.size = Path(path), fps, size
        self.opened, self.empty_output, self.released = opened, empty_output, False
        self.frames = []
        self.path.touch(exist_ok=False)
    def isOpened(self):return self.opened and not self.released
    def write(self, frame):
        self.frames.append(frame.copy())
        with self.path.open('ab') as stream:stream.write(frame.tobytes())
    def release(self):
        self.released=True
        if self.empty_output:self.path.write_bytes(b'')


class WriterFactory:
    def __init__(self, **options):self.writers=[];self.options=options
    def __call__(self, path, fps, size):
        writer=FakeWriter(path,fps,size,**self.options)
        self.writers.append(writer)
        return writer


def frame():return np.arange(3*4*3,dtype=np.uint8).reshape(3,4,3)


def read_manifest(folder):return json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))


class RecorderTests(unittest.TestCase):
    def test_space_records_clean_frames_then_waits_before_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory()
            recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
            original=frame();self.assertFalse(recorder.append(original,1))
            clip=recorder.toggle(original,1)
            self.assertEqual(clip['frame_count'],1)
            recorder.append(original,1.1)
            stopped=recorder.toggle(original,1.3)
            self.assertTrue(stopped['complete']);self.assertIsNone(recorder.active)
            self.assertEqual(recorder.current_action,(1,1,'left_arm'))
            self.assertEqual(len(factory.writers),1)
            for captured in factory.writers[0].frames:np.testing.assert_array_equal(captured,original)
            stamps=[json.loads(line) for line in (folder/stopped['timestamps_path']).read_text().splitlines()]
            self.assertEqual([row['frame_index'] for row in stamps],[0,1])
            self.assertEqual([row['monotonic_seconds'] for row in stamps],[1,1.1])
            self.assertAlmostEqual(stopped['duration_seconds'],.1)
            self.assertAlmostEqual(stopped['observed_fps'],10)
            self.assertEqual(stopped['fps'],30)
            self.assertTrue(stopped['fps_is_nominal'])
            manifest=read_manifest(folder)
            self.assertEqual(manifest['status'],'waiting')
            self.assertEqual(manifest['completed_clips'],1)
            self.assertFalse(manifest['audio_saved'])
            self.assertFalse(stopped['preview_overlay_saved'])

    def test_quit_preserves_completed_and_partial_clips_without_advancing_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory()
            recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
            recorder.toggle(frame(),1);recorder.toggle(frame(),1.2)
            recorder.toggle(frame(),2);recorder.append(frame(),2.1)
            with patch('fpga.demo.record_video.time.monotonic',return_value=2.3):
                partial=recorder.interrupt('q')
            self.assertFalse(partial['complete']);self.assertEqual(partial['status'],'partial')
            self.assertEqual(partial['frame_count'],2)
            manifest=read_manifest(folder)
            self.assertEqual([clip['complete'] for clip in manifest['clips']],[True,False])
            self.assertEqual(manifest['completed_clips'],1)
            self.assertEqual(manifest['status'],'interrupted')
            for clip in manifest['clips']:
                self.assertGreater((folder/clip['path']).stat().st_size,0)
                self.assertTrue((folder/clip['timestamps_path']).is_file())
            self.assertTrue(all(writer.released for writer in factory.writers))
            with self.assertRaises(RuntimeError):recorder.toggle(frame(),3)

    def test_all_eighteen_manually_stopped_segments_complete_three_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory()
            recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
            for index in range(18):
                self.assertIsNone(recorder.active)
                recorder.toggle(frame(),index*2+1)
                recorder.toggle(frame(),index*2+2)
            self.assertTrue(recorder.finished)
            manifest=read_manifest(folder)
            self.assertEqual(manifest['format'],MANIFEST_FORMAT)
            self.assertEqual(manifest['status'],'complete')
            self.assertEqual(manifest['completed_clips'],18)
            self.assertEqual([c['label'] for c in manifest['clips']],list(DEFAULT_LABELS)*3)
            self.assertEqual(len({c['session'] for c in manifest['clips']}),18)
            self.assertTrue(all(c['complete'] for c in manifest['clips']))

    def test_manifest_is_checkpointed_and_timestamp_rows_flush_during_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory()
            recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
            self.assertEqual(read_manifest(folder)['status'],'waiting')
            clip=recorder.toggle(frame(),1)
            self.assertEqual(read_manifest(folder)['clips'][0]['frame_count'],1)
            recorder.append(frame(),1.2)
            self.assertEqual(len((folder/clip['timestamps_path']).read_text().splitlines()),2)
            recorder.append(frame(),2.2)
            self.assertEqual(read_manifest(folder)['clips'][0]['frame_count'],3)
            self.assertFalse((folder/'.manifest.json.tmp').exists())
            with patch('fpga.demo.record_video.time.monotonic',return_value=2.3):recorder.interrupt()

    def test_existing_output_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);sentinel=folder/'existing.avi';sentinel.write_bytes(b'existing user video')
            with self.assertRaises(FileExistsError):
                VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,WriterFactory())
            self.assertEqual(sentinel.read_bytes(),b'existing user video')
            self.assertFalse((folder/'manifest.json').exists())

    def test_writer_open_and_empty_output_errors_never_claim_complete(self):
        for options in ({'opened':False},{'empty_output':True}):
            with self.subTest(options=options),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)/'videos';factory=WriterFactory(**options)
                recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
                with self.assertRaises(RuntimeError):
                    recorder.toggle(frame(),1)
                    recorder.toggle(frame(),2)
                manifest=read_manifest(folder)
                self.assertEqual(manifest['status'],'error')
                self.assertEqual(manifest['completed_clips'],0)
                self.assertFalse(manifest['clips'][0]['complete'])
                self.assertEqual(manifest['clips'][0]['status'],'failed')
                self.assertTrue(factory.writers[0].released)

    def test_size_dtype_and_timestamp_errors_do_not_encode_extra_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory()
            recorder=VideoSessionRecorder(folder,DEFAULT_LABELS,3,4,3,30,factory)
            recorder.toggle(frame(),1)
            for bad,stamp in [(np.zeros((4,4,3),dtype=np.uint8),1.1),
                              (frame().astype(np.float32),1.1),(frame(),1),(frame(),float('nan'))]:
                with self.assertRaises(ValueError):recorder.append(bad,stamp)
            self.assertEqual(len(factory.writers[0].frames),1)
            with patch('fpga.demo.record_video.time.monotonic',return_value=2):
                recorder.interrupt('error','Frame validation failed')
            manifest=read_manifest(folder)
            self.assertEqual(manifest['status'],'error')
            self.assertFalse(manifest['clips'][0]['complete'])
            self.assertEqual(manifest['clips'][0]['frame_count'],1)


class FakeCamera:
    def __init__(self, frames):self.frames=iter(frames);self.released=False
    def read(self):
        try:return True,next(self.frames).copy()
        except StopIteration:return False,None
    def release(self):self.released=True


class RecorderLoopTests(unittest.TestCase):
    def fake_cv(self, factory, keys, visible):
        keys,visible=iter(keys),iter(visible)
        return SimpleNamespace(WINDOW_NORMAL=0,WND_PROP_VISIBLE=1,error=RuntimeError,
            VideoWriter=lambda path,codec,fps,size:factory(path,fps,size),VideoWriter_fourcc=lambda *x:0,
            namedWindow=lambda *x:None,resizeWindow=lambda *x:None,
            imshow=lambda *x:None,destroyAllWindows=lambda:None,
            flip=lambda image,*x:image[:,::-1].copy(),waitKey=lambda *x:next(keys),
            getWindowProperty=lambda *x:next(visible))

    def test_loop_encodes_raw_frames_before_header_and_has_no_pose_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory();originals=[frame(),frame()+1,frame()+2]
            cap=FakeCamera(originals);cv=self.fake_cv(factory,[32,32,ord('q')],[1,1,1])
            args=SimpleNamespace(output_dir=folder,labels=DEFAULT_LABELS,rounds=3)
            # An unmistakably altered preview must never reach the encoder.
            preview=lambda image,*args:np.full((8,4,3),255,dtype=np.uint8)
            with patch.dict(sys.modules,{'cv2':cv}),patch('fpga.demo.record_video._open_camera',return_value=(cap,{'fps_reported':30})),\
                 patch('fpga.demo.record_video._chinese_font',return_value=None),patch('fpga.demo.record_video._draw_capture_text',side_effect=preview),\
                 patch('fpga.demo.record_video.time.monotonic',side_effect=[1,1.1,1.2]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(args),130)
            self.assertTrue(cap.released)
            self.assertEqual(len(factory.writers),1)
            self.assertEqual(len(factory.writers[0].frames),2)
            for actual,expected in zip(factory.writers[0].frames,originals):np.testing.assert_array_equal(actual,expected)
            self.assertTrue(read_manifest(folder)['clips'][0]['complete'])

    def test_window_close_finalizes_active_clip_as_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'videos';factory=WriterFactory();cap=FakeCamera([frame(),frame()])
            cv=self.fake_cv(factory,[32,255],[1,0]);args=SimpleNamespace(output_dir=folder,labels=DEFAULT_LABELS,rounds=3)
            with patch.dict(sys.modules,{'cv2':cv}),patch('fpga.demo.record_video._open_camera',return_value=(cap,{'fps_reported':30})),\
                 patch('fpga.demo.record_video._chinese_font',return_value=None),patch('fpga.demo.record_video._draw_capture_text',side_effect=lambda image,*args:image),\
                 patch('fpga.demo.record_video.time.monotonic',side_effect=[1,1.1,1.2]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(args),130)
            clip=read_manifest(folder)['clips'][0]
            self.assertEqual(clip['ended_by'],'window_close')
            self.assertFalse(clip['complete']);self.assertEqual(clip['status'],'partial')
            self.assertEqual(clip['frame_count'],2)
            self.assertTrue(factory.writers[0].released)


if __name__=='__main__':unittest.main()
