"""Paths and portable launch files for FPGA work outside the Git checkout."""
import os
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent.parent


def external(path):
    path = Path(path).expanduser().resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return path
    raise ValueError("FPGA outputs must be outside the repository: " + str(path))


def workspace(value=None):
    return external(value or os.environ.get("FPGA_WORKSPACE") or ROOT.parent / "fpga_workspace")


def firmware_dir(value=None, work=None):
    return external(value) if value else workspace(work) / "firmware"


def wsl_path(path):
    text = Path(path).resolve().as_posix()
    if len(text) > 2 and text[1:3] == ":/":
        return "/mnt/" + text[0].lower() + text[2:]
    return text


def write_gdb_launchers(work):
    work = workspace(work)
    directory = work / "gdb"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "load_soc_image.gdb").write_bytes((ROOT / "fpga/load_soc_image.gdb").read_bytes())
    command = "python3 %s --run --workspace %s" % (
        shlex.quote(wsl_path(ROOT / "fpga/firmware_batch.py")), shlex.quote(wsl_path(work)))
    text = ("# Generated for WSL/Linux GDB; working directory may be anywhere.\n"
            "disconnect\nshell " + command + "\n"
            "set $soc_batch_exit = $_shell_exitcode\n"
            "target extended-remote :3333\nmaintenance flush register-cache\n"
            "if $soc_batch_exit != 0\n"
            '  printf "FPGA batch failed (exit=%d); inspect console and saved reports.\\n", $soc_batch_exit\n'
            "end\n")
    (directory / "test_all_firmware.gdb").write_text(text, encoding="utf-8", newline="\n")
    return directory
