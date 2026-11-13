import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'base/test/int8'))
import firmware
from assembler import Assembler
from run_soc_xcelium import PASS_RE,FIELDS

def prologue(a,name):
 if name=='scratch_128':
  a.li(10,0x80001fd0);a.li(11,128);a.li(12,0);a.label('scratch_loop')
  a.sw(12,10);a.addi(12,12,1);a.addi(11,11,-1);a.branch('bne',11,0,'scratch_loop')
  a.lw(13,10);a.li(14,127);a.branch('bne',13,14,'fail')
 else:
  a.la(15,'patch_word');a.li(19,8192);a.add(19,15,19)
  a.la(16,'patch_return1');a.jump('patch_word')
  a.label('patch_return1');a.li(18,1);a.branch('bne',17,18,'fail')
  a.li(18,0x20)
  a.emit((18<<20)|(19<<15)|(2<<7)|0x23,'sb x18, 2(x19) # +8KiB SRAM alias')
  a.emit(0x0000100f,'fence.i')
  a.la(16,'patch_return2');a.jump('patch_word')
  a.label('patch_return2');a.li(18,2);a.branch('bne',17,18,'fail')
  a.li(18,0x00300893);a.sw(18,15);a.emit(0x0000100f,'fence.i')
  a.la(16,'patch_return3');a.jump('patch_word')
  a.label('patch_return3');a.li(18,3);a.branch('bne',17,18,'fail');a.jump('patch_done')
  a.label('patch_word');a.addi(17,0,1)
  a.emit((16<<15)|0x67,'jalr x0, x16, 0')
  a.label('patch_done')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 variant=sys.argv[1];root=ROOT/variant;results=[]
 for name in ('scratch_128','code_patch_alias_byte'):
  source=ROOT/'extra_inputs'/name
  if not source.exists():
   source.mkdir(parents=True)
   class ExtendedAssembler(Assembler):
    def __init__(self):
     super().__init__();prologue(self,name)
   firmware.Assembler=ExtendedAssembler
   firmware.build(source,10000)
  case=root/'test/int8/runs'/name;case.mkdir()
  for f in ('firmware.hex','firmware.S'):shutil.copyfile(source/f,case/f)
  command=['xrun','-64bit','-R','-xmlibdirname',str(root/'test/int8/runs/matched/build/xcelium.d'),'-l',str(case/'xrun.log')]
  p=subprocess.run(command,cwd=str(case),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
  (case/'console.log').write_bytes(p.stdout)
  text=p.stdout.decode(errors='replace');match=PASS_RE.search(text)
  if p.returncode or match is None or '*F,' in text or '*E,' in text:raise RuntimeError(text[-4000:])
  result=dict(zip(FIELDS,map(int,match.groups())))
  result.update(variant=variant,workload=name,seed=10000,firmware_sha256=sha(case/'firmware.hex'),status='PASS')
  (case/'results.json').write_text(json.dumps(result,indent=2)+'\n')
  results.append(result);print(json.dumps(result),flush=True)
 report={'scope':'Same original full SoC TB plus explicit CPU workload before full trained HAR golden checks; scratch timing is not HAR-only latency','generator_sha256':sha(Path(__file__)),'source_snapshot_sha256':sha(root/'snapshot.json'),'cases':results}
 (root/'test/int8/runs/extra_results.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
