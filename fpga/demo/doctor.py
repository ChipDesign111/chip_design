"""Read-only local dependency check. Does not open a camera or program hardware."""
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def inspect(host='127.0.0.1', port=6666):
    result = {'python': sys.executable, 'platform': platform.platform(), 'packages': {}}
    for name in ('numpy', 'torch', 'cv2', 'mediapipe', 'matplotlib'):
        try:
            module = importlib.import_module(name)
            result['packages'][name] = {'version': str(module.__version__), 'available': True}
        except Exception as error:
            result['packages'][name] = {'available': False, 'error': str(error)}
    candidates = [os.environ.get('VIVADO_BIN'), shutil.which('vivado'),
                  'D:/pkuwyh/Vivado/2019.1/bin/vivado.bat']
    result['vivado'] = next((str(Path(p)) for p in candidates if p and Path(p).is_file()), None)
    result['pose_model'] = (ROOT/'tools/local/camera_demo/pose_landmarker_lite.task').is_file()
    try:
        with socket.create_connection((host, port), timeout=.5):
            result['openocd_tcp_listening'] = True
    except OSError:
        result['openocd_tcp_listening'] = False
    result['hardware_verified'] = False
    result['hardware_note'] = 'A listening TCP port is not evidence of a connected or working FPGA.'
    if os.name == 'nt':
        command = "Get-CimInstance Win32_PnPEntity | Where-Object {$_.Name -match 'FTDI|Digilent|Xilinx|USB Serial|Camera'} | Select-Object Name,Status | ConvertTo-Json -Compress"
        try:
            run = subprocess.run(['powershell.exe','-NoProfile','-Command',command],
                capture_output=True, timeout=15)
            result['usb_inventory'] = run.stdout.decode(errors='replace').strip()
        except (OSError, subprocess.TimeoutExpired) as error:
            result['usb_inventory_error'] = str(error)
    return result

if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2, ensure_ascii=False))
