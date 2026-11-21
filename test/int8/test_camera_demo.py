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
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.features import (JOINTS, PoseWindow, append_dataset, feature_metadata,
                                feature_profile_from_metadata, load_dataset, normalize_pose, quantize_features)
from fpga.demo.train_camera import split_sessions
from fpga.demo.camera import (AutoCaptureGate, ManualCaptureGate, FPGAWorker, _chinese_font,
                              StableDisplayFilter, _capture_contract, _draw_capture_text, _live_header, _open_camera, collect, read_camera_model)
from fpga.demo.camera import run_capture


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

    def test_manual_knees_collection_preserves_explicit_profile_for_every_session(self):
        args=SimpleNamespace(rounds=3,labels=('standing','left_arm','right_arm','both_arms','squat','lean'),
                             no_display=False,output=Path('unused.npz'),feature_profile='knees')
        with patch('fpga.demo.camera.run_capture',return_value=True) as capture, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(collect(args))
        self.assertEqual(capture.call_count,18)
        self.assertTrue(all(c.args[0].feature_profile=='knees' and c.args[0].wait_start
                            for c in capture.call_args_list))

    def test_live_feature_profile_comes_from_saved_classifier_not_capture_defaults(self):
        args=SimpleNamespace(window=2,feature_profile='full')
        profile,contract=_capture_contract(args)
        self.assertEqual(profile,'full')
        self.assertEqual(contract,feature_metadata(2))
        trained={'feature_contract':feature_metadata(1,profile='knees')}
        profile,contract=_capture_contract(args,trained)
        self.assertEqual(profile,'knees')
        self.assertIs(contract,trained['feature_contract'])
        self.assertEqual(contract['window_seconds'],1)
        with self.assertRaises(ValueError):
            _capture_contract(SimpleNamespace(window=1,feature_profile='unsupported'))

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

    def test_camera_reader_accepts_both_profiles_and_rejects_mixed_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            model={'trained':True,'network':[64,32,6],'labels':list('abcdef'),
                   'package_tag':'0123456789abcdef','input_scale':.1,'output_scale':.2,
                   'backend_target':'int22-raw-v1','npu_core_starts_per_request':1,'dataset_source':'local-camera'}
            live={'package_tag':model['package_tag'],'input_bytes':64,'output_bytes':6,
                  'input_scale':.1,'output_scale':.2}
            (folder/'manifest.json').write_text(json.dumps({'live_demo':live,'target':'int22-raw-v1',
                                                           'npu_core_starts':1}),encoding='utf-8')
            for profile in ('full','knees','video','image','flow'):
                model['feature_contract']=feature_metadata(.25 if profile=='flow' else 1,profile=profile)
                if profile=='flow':model['feature_contract']['train_feature_scale']=[1.0]*64
                (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
                self.assertEqual(feature_profile_from_metadata(read_camera_model(folder)['feature_contract']),profile)
            model['dataset_source']='local-camera+public-templates'
            model['feature_contract']['capture_source']=model['dataset_source']
            model['public_template_sources']=[{'dataset':'UTD-MHAD','action':'right hand wave'}]
            (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
            self.assertEqual(read_camera_model(folder)['dataset_source'],model['dataset_source'])
            del model['public_template_sources']
            (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'public-template provenance'):
                read_camera_model(folder)
            model['dataset_source']='local-camera'
            model['feature_contract']=feature_metadata(profile='knees')
            model['feature_contract']['joints']=list(JOINTS)
            (folder/'camera_demo.json').write_text(json.dumps(model),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'joint/coordinate'):
                read_camera_model(folder)

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


class LiveHeaderTests(unittest.TestCase):
    labels = ['standing','left_arm','right_arm','both_arms','squat','lean']

    def result(self, **changes):
        values = dict(backend='openocd-jtag',class_id=1,sequence=7,roundtrip_ms=120,cycles=42,values=[0,10,0,0,0,0])
        values.update(changes)
        return SimpleNamespace(**values)

    def test_connection_and_waiting_never_fabricate_a_prediction(self):
        for status in ('FPGA connecting...', 'FPGA ready', 'FPGA computing...'):
            english,chinese = _live_header(status,None,None,10,self.labels,.25,.25)
            self.assertIn('WAITING',english[0])
            self.assertEqual(chinese[0],'FPGA 实时识别：等待结果')
        self.assertIn('连接中',_live_header('FPGA connecting...',None,None,10,self.labels,.25,.25)[1][1])

    def test_fresh_hardware_result_has_chinese_action_latency_and_sequence(self):
        stable = StableDisplayFilter()
        for sequence, stamp in [(5,9.3),(6,9.55),(7,9.8)]:
            display=stable.update('FPGA ready',self.result(sequence=sequence),stamp,stamp+.1)
        _,chinese = _live_header('FPGA ready',self.result(),9.8,10,self.labels,.25,.25,display=display)
        self.assertEqual(chinese[0],'FPGA 实时识别：左臂抬起')
        self.assertIn('原始 FPGA',chinese[1])
        self.assertIn('序号 7',chinese[2]);self.assertIn('120 毫秒',chinese[2])
        self.assertIn('左右臂可能混淆',chinese[-1])

    def test_old_result_is_expired_history_instead_of_current_action(self):
        english,chinese = _live_header('FPGA computing...',self.result(),5,10,self.labels,.25,.25)
        self.assertIn('WAITING',english[0])
        self.assertEqual(chinese[0],'FPGA 实时识别：等待结果')
        self.assertIn('已过期',chinese[1])

    def test_error_and_nonhardware_results_cannot_display_old_prediction(self):
        for status,result in [('FPGA ERROR: disconnected',self.result()),
                              ('FPGA ready',self.result(backend='reference'))]:
            _,chinese = _live_header(status,result,9.8,10,self.labels,.25,.25)
            self.assertEqual(chinese[0],'FPGA 实时识别：连接失败')
            self.assertFalse(any('左臂抬起' in line for line in chinese))

    def test_duplicate_frames_cannot_confirm_and_three_sequences_need_time_span(self):
        stable=StableDisplayFilter()
        for now in (10.01,10.02,10.03,10.04):
            display=stable.update('FPGA ready',self.result(sequence=1),10,now)
            self.assertEqual(display.phase,'recognizing');self.assertEqual(display.observations,1)
        stable.update('FPGA ready',self.result(sequence=2),10.1,10.11)
        display=stable.update('FPGA ready',self.result(sequence=3),10.2,10.21)
        self.assertEqual(display.phase,'recognizing')
        display=stable.update('FPGA ready',self.result(sequence=4),10.5,10.51)
        self.assertEqual(display.phase,'confirmed');self.assertEqual(display.class_id,1)

    def test_bounce_low_margin_expiry_and_connection_error_clear_confirmation(self):
        stable=StableDisplayFilter()
        for sequence,stamp in [(1,10),(2,10.25),(3,10.5)]:
            display=stable.update('FPGA ready',self.result(sequence=sequence),stamp,stamp+.01)
        self.assertEqual(display.phase,'confirmed')
        bounce=self.result(sequence=4,class_id=2,values=[0,0,10,0,0,0])
        self.assertEqual(stable.update('FPGA ready',bounce,10.75,10.76).phase,'recognizing')
        low=self.result(sequence=5,class_id=2,values=[0,0,10,9,0,0])
        self.assertEqual(stable.update('FPGA ready',low,11,11.01).phase,'uncertain')
        self.assertIsNone(stable.state.class_id)
        self.assertEqual(stable.update('FPGA ready',low,11,12.3).phase,'expired')
        self.assertEqual(stable.update('FPGA ERROR: disconnected',low,11,12.3).phase,'error')
        self.assertEqual(stable.update('FPGA ready',self.result(sequence=1),13,13.01).observations,1)

    def test_wrong_source_or_changed_duplicate_cannot_be_stable(self):
        stable=StableDisplayFilter()
        original=self.result(sequence=1)
        stable.update('FPGA ready',original,10,10.01)
        changed=self.result(sequence=1,class_id=2,values=[0,0,10,0,0,0])
        self.assertEqual(stable.update('FPGA ready',changed,10,10.02).phase,'uncertain')
        self.assertEqual(stable.update('FPGA ready',self.result(backend='reference'),10,10.03).phase,'error')

    def test_new_input_after_unobserved_long_gap_starts_a_new_vote(self):
        stable=StableDisplayFilter()
        for sequence,stamp in [(1,10),(2,10.25),(3,10.5)]:
            display=stable.update('FPGA ready',self.result(sequence=sequence),stamp,stamp+.01)
        self.assertEqual(display.phase,'confirmed')
        # No GUI update occurred during the gap; the new input itself must
        # invalidate the old votes rather than carry confirmation forward.
        display=stable.update('FPGA ready',self.result(sequence=4),12,12.01)
        self.assertEqual(display.phase,'recognizing');self.assertEqual(display.observations,1)
        self.assertIsNone(display.class_id)

    def test_uncertain_header_keeps_raw_label_transparent_without_confirming_it(self):
        stable=StableDisplayFilter()
        raw=self.result(values=[0,10,9,0,0,0])
        display=stable.update('FPGA ready',raw,9.8,10)
        _,chinese=_live_header('FPGA ready',raw,9.8,10,self.labels,.25,.25,display=display)
        self.assertEqual(chinese[0],'FPGA 实时识别：不确定')
        self.assertIn('原始 FPGA：左臂抬起',chinese[1])
        self.assertEqual(raw.class_id,1);self.assertEqual(raw.values,[0,10,9,0,0,0])

    def test_slow_frontend_keeps_capture_clock_but_ages_ui_at_display_time(self):
        contract=feature_metadata(.25,profile='flow');contract['train_feature_scale']=[1.0]*64
        model={'feature_contract':contract,'labels':self.labels,'dataset_source':'local-camera'}
        frame=np.zeros((96,128,3),np.uint8)
        cap=SimpleNamespace(read=Mock(return_value=(True,frame)),release=Mock())
        extractor=SimpleNamespace(update=Mock(return_value=np.zeros(64,np.float32)))
        raw=self.result(class_id=0,values=[10,0,0,0,0,0])
        worker=SimpleNamespace(submit=Mock(),snapshot=Mock(return_value=('FPGA ready',raw,10.8,9.0)),close=Mock())
        stable=StableDisplayFilter()
        args=SimpleNamespace(command='run',package=Path('unused'),allow_synthetic_engineering_test=False,
                             seconds=.5,interval=.25,no_display=True,host='localhost',port=6666,
                             timeout=1,attach=True,session='')
        output=io.StringIO()
        with patch('fpga.demo.camera.read_camera_model',return_value=model), \
             patch('fpga.demo.camera._open_camera',return_value=(cap,{})), \
             patch('fpga.demo.flow_features.FlowFeatureExtractor',return_value=extractor), \
             patch('fpga.demo.camera.FPGAWorker',return_value=worker), \
             patch('fpga.demo.camera.StableDisplayFilter',return_value=stable), \
             patch.object(stable,'update',wraps=stable.update) as update_display, \
             patch('fpga.demo.camera._live_header',wraps=_live_header) as header, \
             patch('fpga.demo.camera.time.monotonic',side_effect=[10.0,10.1,10.9]), \
             contextlib.redirect_stdout(output):
            self.assertTrue(run_capture(args))
        self.assertAlmostEqual(extractor.update.call_args.args[0],10.1)
        self.assertAlmostEqual(worker.submit.call_args.args[1],10.1)
        self.assertAlmostEqual(update_display.call_args.args[3],10.9)
        self.assertAlmostEqual(header.call_args.args[3],10.9)
        self.assertEqual(stable.state.phase,'expired')
        events=[json.loads(line) for line in output.getvalue().splitlines()]
        event=next(item for item in events if item.get('event')=='fpga_result')
        self.assertAlmostEqual(event['input_age_ms'],1900)
        self.assertEqual(event['class_id'],0);self.assertEqual(event['scores'],[10,0,0,0,0,0])
        self.assertEqual(event['backend'],'openocd-jtag')
        worker.close.assert_called_once();cap.release.assert_called_once()

    def test_static_frontend_dispatch_and_no_person_clear_previous_confirmation(self):
        for detected in (True,False):
            with self.subTest(person_detected=detected):
                contract={'schema':'yolo11_hip_mask_static64_v1','window_seconds':.25}
                model={'feature_contract':contract,'labels':self.labels,'dataset_source':'local-camera'}
                frame=np.zeros((96,128,3),np.uint8)
                cap=SimpleNamespace(read=Mock(return_value=(True,frame)),release=Mock())
                features=np.zeros(64,np.float32) if detected else None
                extractor=SimpleNamespace(update=Mock(return_value=features))
                create_extractor=Mock(return_value=extractor)
                static_module=SimpleNamespace(StaticPoseFeatureExtractor=create_extractor,
                                               DEFAULT_STATIC_MODEL=Path('default-unused.onnx'))
                raw=self.result(sequence=3)
                worker=SimpleNamespace(submit=Mock(),snapshot=Mock(return_value=('FPGA ready',raw,10.2,9.6)),close=Mock())
                stable=StableDisplayFilter()
                for sequence,stamp in [(1,9.1),(2,9.35),(3,9.6)]:
                    stable.update('FPGA ready',self.result(sequence=sequence),stamp,stamp+.01)
                self.assertEqual(stable.state.phase,'confirmed')
                args=SimpleNamespace(command='run',package=Path('unused'),allow_synthetic_engineering_test=False,
                                     seconds=.1,interval=.25,no_display=True,host='localhost',port=6666,
                                     timeout=1,attach=True,session='',static_pose_model=Path('selected.onnx'))
                output=io.StringIO()
                with patch.dict(sys.modules,{'fpga.demo.static_features':static_module}), \
                     patch('fpga.demo.camera.read_camera_model',return_value=model), \
                     patch('fpga.demo.camera._capture_contract',return_value=('static',contract)), \
                     patch('fpga.demo.camera._open_camera',return_value=(cap,{})), \
                     patch('fpga.demo.camera.FPGAWorker',return_value=worker), \
                     patch('fpga.demo.camera.StableDisplayFilter',return_value=stable), \
                     patch('fpga.demo.camera._live_header',wraps=_live_header) as header, \
                     patch('fpga.demo.camera.time.monotonic',side_effect=[10.0,10.1,10.3]), \
                     contextlib.redirect_stdout(output):
                    self.assertTrue(run_capture(args))
                create_extractor.assert_called_once_with(model_path=Path('selected.onnx'),window_seconds=.25)
                self.assertIs(extractor.update.call_args.args[1],frame)
                self.assertIsNone(extractor.update.call_args.args[2])
                if detected:
                    worker.submit.assert_called_once()
                else:
                    worker.submit.assert_not_called()
                    self.assertEqual(stable.state.phase,'no_person')
                    self.assertIsNone(stable.state.class_id)
                    lines=_live_header(*header.call_args.args,**header.call_args.kwargs)[1]
                    self.assertEqual(lines[0],'FPGA 实时识别：未检测到人物')
                    self.assertFalse(any('左臂抬起' in line for line in lines))
                worker.close.assert_called_once();cap.release.assert_called_once()


if __name__=='__main__':unittest.main()
