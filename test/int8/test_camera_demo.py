"""Camera feature/training contract tests; no camera or board results claimed."""
import json
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import threading
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.features import (JOINTS, PoseWindow, append_dataset, feature_metadata,
                                load_dataset, normalize_pose, quantize_features)
from fpga.demo.train_camera import split_sessions
from fpga.demo.camera import (AutoCaptureGate, ManualCaptureGate, FPGAWorker, _chinese_font,
                              _draw_capture_text, _open_camera, collect, read_camera_model)


def landmarks():
    p = np.zeros((33,4), dtype=np.float32)
    p[:,3] = 1
    for i in JOINTS:
        p[i,:2] = (.3+(i%2)*.3, .2+(i-11)*.025)
    p[11,:2],p[12,:2],p[23,:2],p[24,:2] = (.3,.2),(.6,.2),(.35,.5),(.55,.5)
    return p


class CameraStub:
    def __init__(self, opened=True, backend='DSHOW'):
        self.opened, self.backend, self.released = opened, backend, False
        self.settings = []
    def isOpened(self):return self.opened
    def release(self):self.released=True
    def getBackendName(self):return self.backend
    def set(self, prop, value):
        self.settings.append((prop,value))
        return prop != 27 or value == 100
    def get(self, prop):return {3:1280,4:720,5:30,27:100}[prop]


class CvCameraStub:
    CAP_DSHOW, CAP_MSMF, CAP_ANY = 700, 1400, 0
    CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, CAP_PROP_FPS, CAP_PROP_ZOOM = 3, 4, 5, 27
    def __init__(self, *cameras):self.cameras=list(cameras);self.calls=[]
    def VideoCapture(self, index, api):
        self.calls.append((index,api));return self.cameras.pop(0)


class FeaturesTest(unittest.TestCase):
    def test_translation_scale_invariance_and_aspect_ratio(self):
        p = landmarks(); first = normalize_pose(p,640,480)
        q=p.copy(); q[:,:2]=p[:,:2]*.7+.1
        np.testing.assert_allclose(first, normalize_pose(q,640,480), atol=2e-6)
        # x/y normalized by image dimensions, so a 2x wider copy has same pose.
        q=p.copy();q[:,0]*=.5
        np.testing.assert_allclose(first, normalize_pose(q,1280,480), atol=2e-6)

    def test_missing_joint_is_not_zero_filled(self):
        p = landmarks(); p[31,3]=.2
        self.assertIsNone(normalize_pose(p,640,480))
        p = landmarks();p[11,:2]=p[12,:2]
        self.assertIsNone(normalize_pose(p,640,480))

    def test_window_layout_continuity_and_reset(self):
        w=PoseWindow(1);p=np.zeros((16,2),dtype=np.float32)
        for i in range(10):self.assertIsNone(w.update(i/10,p))
        p[:,0]=.6
        v=w.update(1,p)
        np.testing.assert_allclose(v[:32].reshape(16,2)[:,0], .2)
        np.testing.assert_allclose(v[32:].reshape(16,2)[:,0], .2)
        self.assertEqual(v.shape,(64,))
        self.assertIsNone(w.update(1.3,None))
        self.assertIsNone(w.update(1.4,p))
        with self.assertRaises(ValueError):w.update(1.4,p)

    def test_quantizer_matches_compiler_ties_and_clipping(self):
        x=np.resize(np.array([.5,1.5,-.5,-1.5,1000,-1000],dtype=np.float32),64)
        expected=np.clip(np.rint(x),-128,127).astype(np.int8)
        np.testing.assert_array_equal(quantize_features(x,1),expected)
        with self.assertRaises(ValueError):quantize_features(x,0)
        x[1]=np.nan
        with self.assertRaises(ValueError):quantize_features(x,1)

    def test_dataset_append_contract_and_session_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'features.npz';m=feature_metadata();m['capture_source']='synthetic-engineering-test'
            for c in range(6):
                for session in range(3):
                    append_dataset(p,np.ones((4,64),dtype=np.float32)*c/6,f'c{c}',f'c{c}_s{session}',np.arange(4),m)
            d,loaded=load_dataset(p);self.assertEqual(loaded,m)
            split,assignment=split_sessions(d['labels'],d['sessions'],tuple(f'c{i}' for i in range(6)))
            all_indices=[]
            for name,indices in split.items():
                self.assertEqual(len(set(d['labels'][indices])),6)
                self.assertTrue(all(assignment[str(s)]==name for s in d['sessions'][indices]))
                all_indices.extend(indices)
            self.assertEqual(sorted(all_indices),list(range(72)))
            changed=dict(m,window_seconds=2)
            with self.assertRaises(ValueError):append_dataset(p,np.ones((1,64)), 'c0','new',[5],changed)
            with self.assertRaises(ValueError):append_dataset(p,np.ones((1,64)), 'c1','c0_s0',[5],m)

    def test_not_enough_sessions_is_rejected(self):
        with self.assertRaises(ValueError):
            split_sessions(np.array(['a']*5),np.array(['s']*5),('a',))

    def test_uci_package_is_not_camera_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):read_camera_model(tmp)
            p=Path(tmp)/'camera_demo.json'
            p.write_text(json.dumps({'trained':False}),encoding='utf-8')
            with self.assertRaises(ValueError):read_camera_model(tmp)

    def test_guided_collect_has_distinct_confirmed_sessions_and_stops_on_q(self):
        labels=tuple(f'action{i}' for i in range(6))
        args=SimpleNamespace(rounds=3,labels=labels,no_display=False,output=Path('unused.npz'))
        with patch('fpga.demo.camera.run_capture',return_value=True) as capture, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(collect(args))
            options=[c.args[0] for c in capture.call_args_list]
            self.assertEqual(len(options),18)
            self.assertEqual(len({o.session for o in options}),18)
            self.assertTrue(all(o.wait_start and o.command=='record' for o in options))
        with patch('fpga.demo.camera.run_capture',side_effect=[True,False]) as capture, contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(collect(args));self.assertEqual(capture.call_count,2)

    def test_auto_collect_all_eighteen_sessions_without_space(self):
        labels=('standing','left_arm','right_arm','both_arms','squat','lean')
        args=SimpleNamespace(rounds=3,labels=labels,no_display=False,output=Path('unused.npz'),
                             auto_advance=True,pose_timeout=120)
        with patch('fpga.demo.camera.run_capture',return_value=True) as capture, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(collect(args))
        options=[call.args[0] for call in capture.call_args_list]
        self.assertEqual([o.label for o in options],list(labels)*3)
        self.assertEqual(len({o.session for o in options}),18)
        self.assertTrue(all(o.auto_advance and not o.wait_start for o in options))
        self.assertIn('站立',options[0].progress_zh)
        self.assertIn('第 3/3 轮',options[-1].progress_zh)

    def test_auto_waits_for_valid_full_body_and_restarts_interrupted_countdown(self):
        gate=AutoCaptureGate(2,2,.5,timeout=20)
        self.assertEqual(gate.tick(0,False).phase,'waiting')
        self.assertEqual(gate.tick(8,False).phase,'waiting')
        self.assertEqual(gate.tick(9,True).phase,'preparing')
        self.assertEqual(gate.tick(10,False).phase,'waiting')
        self.assertEqual(gate.tick(11,True).phase,'preparing')
        self.assertEqual(gate.tick(12.9,True).phase,'preparing')
        first=gate.tick(13,True)
        self.assertTrue(first.emit)
        self.assertEqual(first.phase,'recording')
        self.assertEqual(gate.windows,1)

    def test_auto_never_finishes_empty_or_too_small_segment_and_retries_same_gate(self):
        gate=AutoCaptureGate(1,2,.5,timeout=20)
        self.assertEqual(gate.minimum,2)
        gate.tick(0,True)
        self.assertTrue(gate.tick(1,True).emit)
        self.assertFalse(gate.tick(1.5,False).emit)
        rejected=gate.tick(3,False)
        self.assertEqual(rejected.phase,'retry')
        self.assertTrue(rejected.discard)
        self.assertEqual(rejected.windows,1)
        self.assertEqual(gate.windows,0)
        self.assertEqual(gate.retries,1)
        self.assertEqual(gate.tick(3.1,False).phase,'waiting')
        gate.tick(4,True)
        self.assertTrue(gate.tick(5,True).emit)
        self.assertFalse(gate.tick(5.2,True).emit)
        self.assertTrue(gate.tick(5.5,True).emit)
        self.assertFalse(gate.tick(6,False).emit)
        complete=gate.tick(7,False)
        self.assertEqual(complete.phase,'complete')
        self.assertEqual(complete.windows,2)
        self.assertFalse(complete.emit)

    def test_auto_timeout_is_bounded_across_retries_and_bad_settings_fail(self):
        gate=AutoCaptureGate(1,2,.5,timeout=5)
        gate.tick(10,False)
        with self.assertRaisesRegex(RuntimeError,'completed sessions are preserved'):
            gate.tick(15,False)
        gate=AutoCaptureGate(1,2,.5,timeout=5)
        gate.tick(0,True);gate.tick(1,True);gate.tick(3,False)
        self.assertEqual(gate.retries,1)
        with self.assertRaisesRegex(RuntimeError,'timed out'):
            gate.tick(5,False)
        for settings in [(float('nan'),2,.5,10),(1,0,.5,10),(1,2,.5,3)]:
            with self.assertRaises(ValueError):AutoCaptureGate(*settings)
        gate=AutoCaptureGate(1,2,.5,timeout=5)
        gate.tick(1,False)
        with self.assertRaises(ValueError):gate.tick(.5,True)

    def test_manual_empty_segment_waits_for_space_to_retry_same_action(self):
        gate=ManualCaptureGate(2,2,.5)
        self.assertEqual(gate.tick(0,True).phase,'waiting')
        self.assertEqual(gate.tick(10,True).phase,'waiting')
        self.assertEqual(gate.tick(11,False,confirm=True).phase,'preparing')
        self.assertEqual(gate.tick(13,False).phase,'recording')
        rejected=gate.tick(15,False)
        self.assertEqual(rejected.phase,'retry')
        self.assertTrue(rejected.discard)
        self.assertEqual(rejected.windows,0)
        self.assertEqual(gate.tick(1000,True).phase,'waiting')
        gate.tick(1001,True,confirm=True)
        self.assertTrue(gate.tick(1003,True).emit)
        self.assertTrue(gate.tick(1003.5,True).emit)
        self.assertEqual(gate.tick(1005,True).phase,'complete')

    def test_manual_short_segment_never_completes_or_restarts_itself(self):
        gate=ManualCaptureGate(1,2,.5,wait_start=False)
        self.assertEqual(gate.tick(0,False).phase,'preparing')
        self.assertTrue(gate.tick(1,True).emit)
        self.assertFalse(gate.tick(1.5,False).emit)
        rejected=gate.tick(3,False)
        self.assertEqual(rejected.phase,'retry')
        self.assertEqual(rejected.windows,1)
        self.assertEqual(gate.tick(4,True).phase,'waiting')
        self.assertEqual(gate.windows,0)

    def test_windows_camera_prefers_dshow_and_reports_real_mode_and_refused_zoom(self):
        cap=CameraStub();cv= CvCameraStub(cap)
        args=SimpleNamespace(camera=0,camera_backend='auto',width=640,height=480,zoom=50)
        with patch('fpga.demo.camera.os.name','nt'):
            opened,info=_open_camera(args,cv)
        self.assertIs(opened,cap)
        self.assertEqual(cv.calls,[(0,cv.CAP_DSHOW)])
        self.assertEqual(cap.settings,[(3,640),(4,480),(27,50)])
        self.assertEqual((info['width_requested'],info['height_requested']),(640,480))
        self.assertEqual((info['width_reported'],info['height_reported']),(1280,720))
        self.assertFalse(info['zoom_set_accepted'])
        self.assertEqual(info['zoom_reported'],100)
        self.assertFalse(info['preview_crop'])

    def test_camera_auto_falls_back_only_on_open_failure_and_explicit_backend_is_strict(self):
        failed,good=CameraStub(False),CameraStub(backend='MSMF')
        cv=CvCameraStub(failed,good)
        args=SimpleNamespace(camera=0,camera_backend='auto',width=1280,height=720,zoom=None)
        with patch('fpga.demo.camera.os.name','nt'):
            _,info=_open_camera(args,cv)
        self.assertEqual(cv.calls,[(0,cv.CAP_DSHOW),(0,cv.CAP_ANY)])
        self.assertTrue(failed.released)
        self.assertEqual(info['backend_actual'],'MSMF')
        self.assertIsNone(info['zoom_set_accepted'])
        self.assertFalse(any(prop==27 for prop,value in good.settings))
        args.camera_backend='dshow';failed=CameraStub(False);cv=CvCameraStub(failed,good)
        with self.assertRaises(RuntimeError):_open_camera(args,cv)
        self.assertEqual(cv.calls,[(0,cv.CAP_DSHOW)])

    def test_invalid_camera_options_do_not_open_a_device(self):
        for key,value in [('width',0),('height',-1),('width',640.5),('zoom',float('nan')),
                          ('zoom',0),('camera',-1),('camera_backend','fake-wide-angle')]:
            options=dict(camera=0,camera_backend='auto',width=1280,height=720,zoom=None)
            options[key]=value;cv=CvCameraStub()
            with self.assertRaises(ValueError):_open_camera(SimpleNamespace(**options),cv)
            self.assertFalse(cv.calls)

    def test_chinese_header_keeps_every_preview_pixel_and_original_geometry(self):
        font=_chinese_font(640)
        if font is None:self.skipTest('No local Chinese font; runtime retains English fallback')
        frame=np.arange(480*640*3,dtype=np.uint8).reshape(480,640,3)
        original=frame.copy()
        result=_draw_capture_text(frame,[],['当前动作：站立','准备动作，倒计时 10 秒'],font,None)
        self.assertGreater(result.shape[0],frame.shape[0])
        self.assertEqual(result.shape[1:],frame.shape[1:])
        self.assertEqual(result.dtype,np.uint8)
        self.assertTrue(result.flags.c_contiguous)
        np.testing.assert_array_equal(result[-frame.shape[0]:],original)
        np.testing.assert_array_equal(frame,original)

    def test_english_fallback_header_does_not_crop_or_cover_preview(self):
        frame=np.arange(48*64*3,dtype=np.uint8).reshape(48,64,3)
        original=frame.copy()
        def put_text(header,*args):header[0,0]=(1,2,3)
        cv=SimpleNamespace(putText=put_text,FONT_HERSHEY_SIMPLEX=0,LINE_AA=0)
        result=_draw_capture_text(frame,['WAITING','SPACE to start'],[],None,cv)
        self.assertEqual(result.shape,(48+60,64,3))
        np.testing.assert_array_equal(result[-48:],original)
        np.testing.assert_array_equal(frame,original)

    def test_model_tag_and_quantization_are_bound_to_resident(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            model={'trained':True,'feature_contract':feature_metadata(),'network':[64,32,6],
                   'labels':list('abcdef'),'package_tag':'0123456789abcdef','input_scale':.1,'output_scale':.2,
                   'backend_target':'int22-raw-v1','npu_core_starts_per_request':1,'dataset_source':'local-camera'}
            live={'package_tag':model['package_tag'],'input_bytes':64,'output_bytes':6,
                  'input_scale':.1,'output_scale':.2}
            (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
            manifest={'live_demo':live,'target':'int22-raw-v1','npu_core_starts':1}
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            self.assertEqual(read_camera_model(folder)['package_tag'],model['package_tag'])
            live['package_tag']='1111111111111111'
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'package_tag'):read_camera_model(folder)
            live['package_tag']=model['package_tag'];live['input_scale']=.05
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'quantization'):read_camera_model(folder)
            live['input_scale']=model['input_scale'];manifest['npu_core_starts']=0
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'no real RAW'):read_camera_model(folder)
            manifest['npu_core_starts']=1
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            model['dataset_source']='synthetic-engineering-test'
            (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'synthetic/unknown'):read_camera_model(folder)
            self.assertEqual(read_camera_model(folder,allow_synthetic_engineering_test=True)['dataset_source'],model['dataset_source'])

    def test_worker_closes_inflight_socket_and_never_publishes_after_quit(self):
        entered=threading.Event();closed=threading.Event();timeouts=[]
        class Transport:
            def __init__(self,*args,timeout):timeouts.append(timeout)
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def close(self):closed.set()
        class Client:
            def load(self):pass
            def quantize(self,features):return features
            def infer(self,features):
                entered.set();closed.wait(2)
                return SimpleNamespace(backend='openocd-jtag')
        with patch('fpga.demo.transport.OpenOCDTransport',Transport), patch('fpga.demo.host.DemoClient.from_package',return_value=Client()):
            worker=FPGAWorker('unused','localhost',6666,.2)
            deadline=time.monotonic()+1
            while worker.snapshot()[0]!='FPGA ready' and time.monotonic()<deadline:time.sleep(.005)
            worker.submit(np.zeros(64),12.)
            self.assertTrue(entered.wait(1))
            worker.close()
            self.assertTrue(closed.is_set());self.assertFalse(worker.thread.is_alive())
            self.assertIsNone(worker.snapshot()[1]);self.assertEqual(timeouts,[.2])

    def test_worker_retains_input_time_separately_from_completion(self):
        class Transport:
            def __init__(self,*args,timeout):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def close(self):pass
        class Client:
            def load(self):pass
            def quantize(self,features):return features
            def infer(self,features):return SimpleNamespace(backend='openocd-jtag')
        with patch('fpga.demo.transport.OpenOCDTransport',Transport), patch('fpga.demo.host.DemoClient.from_package',return_value=Client()):
            worker=FPGAWorker('unused','localhost',6666,.2)
            try:
                deadline=time.monotonic()+1
                while worker.snapshot()[0]!='FPGA ready' and time.monotonic()<deadline:time.sleep(.005)
                captured=time.monotonic()-5
                worker.submit(np.zeros(64),captured)
                while worker.snapshot()[1] is None and time.monotonic()<deadline:time.sleep(.005)
                status,result,completed,source=worker.snapshot()
                self.assertIsNotNone(result);self.assertEqual(source,captured)
                self.assertGreater(completed-source,4)
            finally:worker.close()


if __name__=='__main__':unittest.main()
