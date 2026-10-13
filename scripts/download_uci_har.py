"""Fetch the official UCI archive; extract only the test split and attribution."""
import hashlib,io,json
from pathlib import Path
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]
URL="https://archive.ics.uci.edu/static/public/240/human%2Bactivity%2Brecognition%2Busing%2Bsmartphones.zip"
def download():
    out=ROOT/"data";out.mkdir(exist_ok=True)
    archive=out/"uci_har_official.zip"
    if not archive.exists():
        temporary=archive.with_suffix(".partial")
        with urllib.request.urlopen(URL,timeout=60) as response,temporary.open("wb") as output:
            total=0
            while chunk:=response.read(1024*1024):
                output.write(chunk);total+=len(chunk)
                if total%(10*1024*1024)==0: print(f"UCI download {total//1024//1024} MiB",flush=True)
        temporary.replace(archive)
    outer=zipfile.ZipFile(archive)
    nested=[n for n in outer.namelist() if n.endswith("UCI HAR Dataset.zip")]
    dataset=zipfile.ZipFile(io.BytesIO(outer.read(nested[0]))) if nested else outer
    wanted=["test/X_test.txt","test/y_test.txt","test/subject_test.txt","activity_labels.txt","features.txt","README.txt","features_info.txt"]
    manifest={"url":URL,"archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":{}}
    for relative in wanted:
        name="UCI HAR Dataset/"+relative
        raw=dataset.read(name)
        target=out/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        manifest["files"][name]=hashlib.sha256(raw).hexdigest()
    (out/"uci_source.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest),flush=True)
if __name__=="__main__":download()
