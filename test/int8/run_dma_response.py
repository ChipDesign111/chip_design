"""Directed DMA B-channel latency and completion-integrity regression (Icarus)."""
import argparse,datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rtl',type=Path,default=ROOT/'rtl/dma/har_dma.sv');p.add_argument('--out',type=Path);a=p.parse_args()
 out=(a.out or ROOT/'test/int8/runs'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_dma_response')).resolve();out.mkdir(parents=True,exist_ok=False)
 files=[a.rtl.resolve(),ROOT/'test/int8/tb_dma_response.sv',Path(__file__).resolve()]
 hashes={str(f):sha(f) for f in files}
 for name,command in [('compile',['iverilog','-g2012','-s','tb_dma_response','-o',str(out/'test.vvp'),str(files[0]),str(files[1])]),('run',['vvp',str(out/'test.vvp')])]:
  r=subprocess.run(command,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);(out/(name+'.log')).write_bytes(r.stdout)
  text=r.stdout.decode(errors='replace')
  if r.returncode or 'FATAL' in text or 'DMA_RESPONSE_FAIL' in text:raise RuntimeError(text)
 text=(out/'run.log').read_text();matches=re.findall(r'DMA_RESPONSE_CASE kind=(\d+) b_delay=(\d+) last_w_to_done=(\d+) b_to_done=(\d+) reads=(\d+) writes=(\d+) bursts=(\d+) copied=(\d+) elapsed=(\d+)',text)
 assert len(matches)==8 and 'DMA_RESPONSE_PASS checks=8' in text
 assert all(sha(f)==hashes[str(f)] for f in files)
 report={'status':'PASS','source_sha256':hashes,'cases':[dict(zip(['kind','b_delay','last_w_to_done','b_to_done','reads','writes','bursts','copied','elapsed'],map(int,m))) for m in matches],'scope':'Directed RTL DMA only; not full SoC or timing signoff'}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(text);print(out)
if __name__=='__main__':main()
