"""Convert observer-only phase boundaries and trace the remaining full-call defect."""
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
log=(ROOT/'logs/emit-w4-n1024-canonical.log').read_text()
marks=[]
for line in log.splitlines():
    if line.startswith('QIP_PHASE_BOUND '):
        _,pos,name=line.split();marks.append((int(pos),name))
size=next(int(line.split(':')[1]) for line in log.splitlines() if 'emitted ops :' in line)
rows=['phase\tstart\tend']
for (start,name),(end,_) in zip(marks,marks[1:]+[(size,'end')]):
    if start<end:rows.append(f'{name}\t{start}\t{end}')
path=ROOT/'shell-phases.tsv';path.write_text('\n'.join(rows)+'\n')
binary=ROOT/'target/release/eval_repairtrace'
inputs=ROOT.parent/'qip2027-followup-diagnostics/zero-slope.tsv'
with (ROOT/'logs/shell-trace.tsv').open('w') as out,(ROOT/'logs/shell-trace.log').open('w') as err:
    run=subprocess.run([str(binary),str(ROOT/'emit-window-4/ops.bin'),str(inputs),str(path)],env=dict(os.environ,TRACE_LANE='0',EVAL_SHARED_SEED='qip-canonical-reference-targeted-20260909-v1'),stdout=out,stderr=err,check=True)
print('Trace retained in logs/shell-trace.log')
