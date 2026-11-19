"""FPGA entry points; projects, firmware and runtime output stay outside Git."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from fpga.workspace import external, workspace, write_gdb_launchers


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8",newline="\n")


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def vivado_path(value=None):
    value=value or os.environ.get("VIVADO") or shutil.which("vivado") or shutil.which("vivado.bat")
    if not value and os.environ.get("XILINX_VIVADO"):
        value=str(Path(os.environ["XILINX_VIVADO"])/"bin"/("vivado.bat" if os.name == "nt" else "vivado"))
    if not value or not Path(value).is_file():
        raise ValueError("Set VIVADO, put Vivado on PATH, or pass --vivado /path/to/vivado")
    return str(Path(value).resolve())


def launch(command, directory, log):
    directory=external(directory);directory.mkdir(parents=True,exist_ok=True)
    log=external(log);log.parent.mkdir(parents=True,exist_ok=True)
    print("Running: "+" ".join(map(str,command))+"\nLog: "+str(log),flush=True)
    with log.open("wb") as stream:
        result=subprocess.run(list(map(str,command)),cwd=directory,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        tail=log.read_text(errors="replace")[-3000:]
        raise RuntimeError("Command failed (%d): %s\n%s" % (result.returncode,log,tail))


def tcl_word(value):
    value=str(value).replace("\\","/")
    for old,new in (("\"","\\\""),("$","\\$"),("[","\\["),("\n","\\n"),("\r","\\r")):
        value=value.replace(old,new)
    return '"'+value+'"'


def project_config(work, mode="runtime", jobs=1, stage="project"):
    work=workspace(work)
    board=json.loads((ROOT/"fpga/config/board.json").read_text())
    directory=work/"config";directory.mkdir(parents=True,exist_ok=True)
    values=dict(repo=ROOT.as_posix(),project_dir=(work/"final_project").as_posix(),
                firmware=(work/"firmware/int8_selftest.hex").as_posix(),mode=mode,jobs=jobs,stage=stage)
    values.update({k:v for k,v in board.items() if k != "clock_properties"})
    lines=["# Generated outside Git; source paths are supplied by this checkout."]
    lines += ["set cfg(%s) %s" % (k,tcl_word(v)) for k,v in values.items()]
    for key,value in board["clock_properties"].items():
        lines.append("set clock_cfg(%s) %s" % (key,tcl_word(value)))
    path=directory/"project.tcl"
    path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    return path


def initialize(work):
    work = workspace(work)
    write_gdb_launchers(work)
    (work / "config").mkdir(exist_ok=True)
    openocd_config = work / "config/cv32e40p.cfg"
    if not openocd_config.exists():
        openocd_config.write_bytes((ROOT / "fpga/config/cv32e40p.cfg").read_bytes())


def prepare(work, python):
    work=workspace(work);work.mkdir(parents=True,exist_ok=True)
    python=str(Path(python or sys.executable).resolve())
    logdir=work/"logs"/("prepare_"+stamp())
    launch([python,ROOT/"fpga/firmware/generate_images.py","--output-dir",work/"firmware"],work,logdir/"legacy.log")
    launch([python,ROOT/"fpga/firmware/generate_suite.py","--output-dir",work/"firmware/suite"],work,logdir/"suite.log")
    launch([sys.executable,ROOT/"fpga/firmware/validate_images.py","--workspace",work],work,logdir/"validate.log")
    initialize(work)
    save(work/"workspace.json",dict(repository=str(ROOT),workspace=str(work),prepared_at=stamp(),
                                  firmware_manifest_sha256=sha(work/"firmware/image_manifest.json"),
                                  suite_manifest_sha256=sha(work/"firmware/suite/suite_manifest.json")))
    print("FPGA_PREPARE_PASS "+str(work),flush=True)


def build_project(work, vivado, mode, jobs, stage):
    work=workspace(work);work.mkdir(parents=True,exist_ok=True)
    if jobs < 1:
        raise ValueError("jobs must be positive")
    if mode == "preload" and not (work/"firmware/int8_selftest.hex").is_file():
        raise ValueError("Preload firmware missing; run prepare first")
    config=project_config(work,mode,jobs,stage)
    inputs=[p for folder in ("rtl","fpga/src","fpga/tcl","fpga/config")
            for p in (ROOT/folder).rglob("*") if p.is_file()]
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    logdir=work/"logs"/(stage+"_"+stamp())
    manifest=dict(status="RUNNING",source_sha256=sources,mode=mode,stage=stage,
                  project=str(work/"final_project/final_project.xpr"),config_sha256=sha(config))
    save(logdir/"input_manifest.json",manifest)
    try:
        launch([vivado_path(vivado),"-mode","batch","-nojournal","-nolog","-source",
                ROOT/"fpga/tcl/project.tcl","-tclargs",config],work,logdir/"vivado.log")
        if any(sha(ROOT/name) != digest for name,digest in sources.items()):
            raise RuntimeError("Source changed during Vivado operation; use a fresh build")
        manifest["status"]="PASS"
    except Exception as error:
        manifest.update(status="FAIL",error=str(error));raise
    finally:
        save(logdir/"input_manifest.json",manifest)
    print("FPGA_%s_PASS %s" % (stage.upper(),manifest["project"]),flush=True)


def relocate_project(work, old_repo):
    """Repair a moved legacy XPR; leave bitstreams/checkpoints/logs intact."""
    work=workspace(work);old_repo=Path(old_repo).resolve()
    path=work/"final_project/final_project.xpr"
    text=path.read_text(encoding="utf-8")
    replacements={
        (old_repo/"fpga/final_project").as_posix():(work/"final_project").as_posix(),
        (old_repo/"fpga/firmware").as_posix():(work/"firmware").as_posix(),
        (old_repo/"fpga/fpga_top.sv").as_posix():(ROOT/"fpga/src/fpga_top.sv").as_posix(),
        (old_repo/"fpga/fpga_top.xdc").as_posix():(ROOT/"fpga/src/fpga_top.xdc").as_posix(),
        "$PPRDIR/../../rtl":(ROOT/"rtl").as_posix(),
        "$PPRDIR/../fpga_top.sv":(ROOT/"fpga/src/fpga_top.sv").as_posix(),
        "$PPRDIR/../fpga_top.xdc":(ROOT/"fpga/src/fpga_top.xdc").as_posix(),
    }
    for old,new in replacements.items():
        text=text.replace(old,new)
    path.write_text(text,encoding="utf-8",newline="\n")
    write_gdb_launchers(work)
    return path


def collect(work, run, name):
    work=workspace(work)
    if run is None:
        candidates=sorted((work/"tests").glob("fpga_board_*/result.json"))
        if not candidates:
            raise ValueError("No board result found; pass --run /external/result/directory")
        run=candidates[-1].parent
    run=external(run)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+",name) or name in (".",".."):
        raise ValueError("Report name must be a simple directory name")
    result=json.loads((run/"result.json").read_text())
    destination=ROOT/"fpga/results"/name
    destination.mkdir(parents=True,exist_ok=False)
    files={}
    for filename in ("result.json","summary.md","summary.csv","speedups.csv"):
        source=run/filename
        if source.is_file():
            (destination/filename).write_bytes(source.read_bytes());files[filename]=sha(source)
    save(destination/"receipt.json",dict(source_run=str(run),status=result["status"],
                                         environment=result.get("environment"),files_sha256=files))
    print("Collected reports: "+str(destination))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    for name in ("doctor","prepare","project","build","gui","test","validate","collect"):
        command=sub.add_parser(name)
        command.add_argument("--workspace",type=Path)
        if name in ("doctor","project","build","gui"):
            command.add_argument("--vivado")
        if name == "prepare":
            command.add_argument("--compiler-python",type=Path)
        if name in ("project","build"):
            command.add_argument("--mode",choices=("runtime","preload"),default="runtime")
            command.add_argument("--jobs",type=int,default=1)
        if name == "build":
            command.add_argument("--stage",choices=("synth","bitstream"),default="bitstream")
        if name == "validate":
            command.add_argument("--simulate",action="store_true")
            command.add_argument("--vsim",default="vsim")
        if name == "collect":
            command.add_argument("--run",type=Path)
            command.add_argument("--name",default=datetime.datetime.now().strftime("board_%Y%m%d_%H%M%S"))
    args,extra=parser.parse_known_args()
    if extra and args.command != "test":
        parser.error("unrecognized arguments: "+" ".join(extra))
    work=workspace(args.workspace)
    if args.command == "doctor":
        try: tool=vivado_path(args.vivado)
        except ValueError: tool=None
        print(json.dumps(dict(repository=str(ROOT),workspace=str(work),vivado=tool,
                             python=sys.version.split()[0],project_exists=(work/"final_project/final_project.xpr").is_file()),indent=2))
    elif args.command == "prepare":
        prepare(work,args.compiler_python)
    elif args.command in ("project","build"):
        build_project(work,args.vivado,args.mode,args.jobs,"project" if args.command == "project" else args.stage)
    elif args.command == "gui":
        project=work/"final_project/final_project.xpr"
        if not project.is_file():
            raise ValueError("Project missing; run the project command first")
        launch([vivado_path(args.vivado),"-mode","gui",project],work,work/"logs"/("gui_"+stamp()+".log"))
    elif args.command == "test":
        if not work.is_dir():
            raise ValueError("Workspace missing; run prepare first")
        return subprocess.call([sys.executable,str(ROOT/"fpga/firmware_batch.py"),"--run","--workspace",str(work)]+extra,cwd=work)
    elif args.command == "validate":
        if not work.is_dir():
            raise ValueError("Workspace missing; run prepare first")
        command=[sys.executable,str(ROOT/"fpga/firmware/validate_images.py"),"--workspace",str(work)]
        if args.simulate:
            command += ["--simulate","--vsim",args.vsim,"--out",str(work/"presim"/("run_"+stamp()))]
        return subprocess.call(command,cwd=work)
    elif args.command == "collect":
        collect(work,args.run,args.name)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception,KeyboardInterrupt) as error:
        print("FPGA_ERROR: "+str(error),file=sys.stderr);raise SystemExit(1)
