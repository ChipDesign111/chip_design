"""Visible PC integer-reference classification; never represents FPGA output."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'tools/local/camera_demo'
sys.path[:0]=[str(ROOT),str(BASE)]
import cv2
import numpy as np
from fpga.demo.camera import _open_camera,_chinese_font,_draw_capture_text,ACTION_ZH
from fpga.demo.static_features import StaticPoseFeatureExtractor, DEFAULT_STATIC_MODEL
from fpga.demo.pose_overlay import draw_static_pose
from fpga.demo.pc_reference import load_reference, DEFAULT_MODEL, DEFAULT_DATASET

TITLE='Action recognition - PC test'
STATE=BASE/'ACTIVE_PC_RECOGNITION.json'

def save(value):
    tmp=STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(STATE)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=DEFAULT_MODEL)
    parser.add_argument('--dataset',type=Path,default=DEFAULT_DATASET)
    parser.add_argument('--static-pose-model',type=Path,default=DEFAULT_STATIC_MODEL)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--seconds',type=float,default=3600)
    args=parser.parse_args(argv)
    if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('--seconds must be positive')
    BASE.mkdir(parents=True,exist_ok=True)
    package,model=load_reference(args.model,args.dataset)
    print('VERIFIED_PC_INTEGER_MODEL '+model['package_tag'],flush=True)
    extractor=StaticPoseFeatureExtractor(model_path=args.static_pose_model,window_seconds=.25)
    cap,info=_open_camera(SimpleNamespace(camera=args.camera,camera_backend='dshow',width=1280,height=720,zoom=100),cv2)
    status=dict(status='OPENING',backend='pc-integer-reference',fpga_connected=False,pid=os.getpid(),
                package_tag=model['package_tag'],window=TITLE,video_saved=False,audio_saved=False,camera=info,predictions=0)
    save(status)
    frames=0;began=time.monotonic();last_infer=float('-inf');last_saved=began
    candidate=None;first_candidate=None;previous_time=None;count=0;confirmed=None
    raw_label=None;margin=None;compute_ms=0
    try:
        cv2.namedWindow(TITLE,cv2.WINDOW_NORMAL);cv2.resizeWindow(TITLE,1100,800)
        font=None;features=None
        while time.monotonic()-began<args.seconds:
            ok,frame=cap.read();captured=time.monotonic()
            if not ok or frame is None:raise RuntimeError('Camera frame read failed')
            frames+=1
            if font is None:font=_chinese_font(frame.shape[1])
            features=extractor.update(captured,frame)
            if captured-last_infer>=.25:
                last_infer=captured
                if features is None:
                    candidate=first_candidate=previous_time=confirmed=raw_label=margin=None;count=0
                    status.update(status='WAITING_FOR_PERSON',confirmed_label=None,raw_label=None)
                else:
                    started=time.perf_counter()
                    scores=package.reference(features[None,:])[package.graph['output']][0]
                    compute_ms=(time.perf_counter()-started)*1000
                    class_id=int(np.argmax(scores));raw_label=model['labels'][class_id]
                    sorted_scores=np.sort(scores.astype(np.int16));margin=int(sorted_scores[-1]-sorted_scores[-2])
                    if margin<3:
                        candidate=first_candidate=confirmed=None;count=0
                    else:
                        if candidate!=class_id or previous_time is None or captured-previous_time>=1.2:
                            candidate=class_id;first_candidate=captured;count=0
                        count+=1
                        confirmed=raw_label if count>=3 and captured-first_candidate>=.5 else None
                    previous_time=captured
                    status['predictions']+=1
                    status.update(status='PC_RECOGNIZING',raw_label=raw_label,confirmed_label=confirmed,
                                  scores=scores.tolist(),score_gap=margin,classifier_ms=compute_ms,input_at=captured)
            fps=frames/max(captured-began,.001)
            if features is None:headline='电脑识别：等待人物进入画面'
            elif confirmed is not None:headline='电脑识别：'+ACTION_ZH.get(confirmed,confirmed)
            elif margin is not None and margin<3:headline='电脑识别：不确定'
            else:headline='电脑识别：确认动作中'
            raw=ACTION_ZH.get(raw_label,raw_label) if raw_label is not None else '暂无'
            chinese=[headline,
                     f'原始结果：{raw}　分数差 {margin if margin is not None else "—"}　连续确认 {min(count,3)}/3',
                     f'画面 {frame.shape[1]}×{frame.shape[0]}　预览 {fps:.1f} 帧/秒　分类 {compute_ms:.2f} 毫秒',
                     '动作：站立 / 左臂 / 右臂 / 双臂 / 下蹲 / 侧倾；Q 退出']
            english=['PC ACTION RECOGNITION',f'Raw: {raw_label}; confirmed: {confirmed}',
                     'Same frozen INT8 classifier, executed on PC. Q: exit']
            points,visible=extractor.overlay_snapshot()
            frame=draw_static_pose(frame,points,visible)
            preview=_draw_capture_text(cv2.flip(frame,1),english,chinese,font,cv2)
            cv2.imshow(TITLE,preview)
            if frames==1 or captured-last_saved>=2:
                status.update(frames=frames,preview_fps=fps,last_frame_monotonic=captured);save(status)
                print(json.dumps(status,ensure_ascii=False),flush=True);last_saved=captured
            key=cv2.waitKey(1)&255
            if key in (ord('q'),27) or cv2.getWindowProperty(TITLE,cv2.WND_PROP_VISIBLE)<1:break
    except BaseException as error:
        status.update(status='ERROR',error=str(error));save(status);raise
    finally:
        cap.release();cv2.destroyAllWindows()
        if status['status']!='ERROR':status.update(status='CLOSED')
        save(status)

if __name__=='__main__':main()
