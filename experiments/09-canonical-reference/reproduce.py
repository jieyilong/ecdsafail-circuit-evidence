"""Explicit, serial rebuilding in .work; published records remain read-only."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ledger(path,key):
    with path.open() as f:return sorted(csv.DictReader(f,delimiter='\t'),key=lambda r:int(r[key]))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','build','cells','component','emit','stats','targeted','pilot'])
    p.add_argument('--work-dir',type=Path,default=REPO/'.work/canonical-reference-reproduction')
    p.add_argument('--variant',choices=['combined','replay-only'],default='combined',help='Used only by prepare')
    p.add_argument('--w',type=int,choices=[4,16],default=16)
    a=p.parse_args();base=REPO/'.work'
    if base.is_symlink():raise ValueError('.work must not be a symlink')
    base.mkdir(exist_ok=True)
    work=a.work_dir.absolute()
    if not work.resolve().is_relative_to(base.resolve()) or work.resolve()==base.resolve():raise ValueError('Choose a subdirectory under .work/')
    for parent in [work,*work.parents]:
        if parent==REPO:break
        if parent.is_symlink():raise ValueError('Symlinked work paths are not allowed')
    if a.stage=='prepare':
        if work.exists():raise FileExistsError('Prepare requires a new work directory')
        subprocess.run([sys.executable,'-B',str(ROOT/'verify.py')],check=True)
        work.mkdir(parents=True)
        src=ROOT/'source' if a.variant=='combined' else ROOT/'attempts/replay-only/source'
        shutil.copytree(src,work/'source')
        shutil.copytree(ROOT/'fixtures',work/'fixtures')
        shutil.copy2(ROOT/'targeted-driver.rs',work/'source/src/bin/eval_followup.rs')
        if not (work/'source/src/bin/stats_stream.rs').exists():shutil.copy2(ROOT/'source/src/bin/stats_stream.rs',work/'source/src/bin/stats_stream.rs')
        (work/'logs').mkdir()
        (work/'prepared.json').write_text(json.dumps({'variant':a.variant,'release':'v1.3.0','source':str(src)})+'\n')
        print(work);return
    if not (work/'prepared.json').is_file():raise RuntimeError('Run prepare first')
    for path in work.rglob('*'):
        if path.is_symlink():raise ValueError('Symlinks in the work copy are not allowed')
        if path.is_file() and path.relative_to(work).parts[0]!='target' and path.stat().st_nlink>1:raise ValueError('Hardlinked work inputs/outputs are not allowed')
    variant=json.loads((work/'prepared.json').read_text())['variant']
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','LANG','LC_ALL','CARGO_HOME']}
    env.update(QIP_CANONICAL_REPLAY='1',QIP_PINGPONG_PROFILE='guarded',TLM_MSBS='40',CONSTPROP_DISABLE='1',SINGLE_CCX_FANOUT_DISABLE='1',CARGO_BUILD_JOBS='2')
    if variant=='combined':env['QIP_CANONICAL_COORDS']='1'
    # Check watchdog access before launching a potentially large process.
    subprocess.run(['ps','-o','rss=','-p',str(os.getpid())],check=True,capture_output=True)
    def run(command,cwd,name,extra=None):
        out=work/'logs'/f'{name}.out';err=work/'logs'/f'{name}.err'
        if out.exists() or err.exists():raise FileExistsError('Use a fresh work directory or a new stage; logs are never overwritten')
        start=time.time();peak=0
        with out.open('w') as o,err.open('w') as e:
            child=subprocess.Popen(command,cwd=cwd,env=env|dict(extra or {}),stdout=o,stderr=e)
            try:
                while child.poll() is None:
                    rss=subprocess.run(['ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True)
                    if rss.returncode==0 and rss.stdout.strip():peak=max(peak,int(rss.stdout.strip()))
                    if peak>19_000_000 or time.time()-start>1200:raise RuntimeError('RSS/time budget exceeded')
                    time.sleep(.5)
            finally:
                if child.poll() is None:child.kill();child.wait()
        (work/'logs'/f'{name}.json').write_text(json.dumps({'command':command,'cwd':str(cwd),'exit_code':child.returncode,'seconds':time.time()-start,'peak_kib':peak,'variant':variant},indent=2)+'\n')
        if child.returncode:raise RuntimeError(f'{name} failed; inspect {err}')
        return out,err
    binary=work/'target/release'
    emitted=work/f'emit-w{a.w}'
    record_root=ROOT if variant=='combined' else ROOT/'attempts/replay-only'
    if a.stage=='build':
        run(['cargo','build','--release','--locked','--offline','--manifest-path','source/Cargo.toml','--target-dir','target','--bin','build_circuit','--bin','eval_bounded','--bin','eval_followup','--bin','stats_stream'],work,'build')
    elif a.stage in ['cells','component']:
        out,_=run([str(binary/'build_circuit')],work/'source',a.stage,{'QIP_BOUNDARY_MODE':a.stage})
        expected=record_root/'logs'/f'{a.stage}-w4-n1024-canonical.log'
        assert out.read_bytes()==expected.read_bytes(),'Diagnostic differs from recorded log'
    elif a.stage=='emit':
        emitted.mkdir(exist_ok=True)
        if (emitted/'ops.bin').exists():raise FileExistsError('Existing operation stream')
        extra={'WINDOWED_MODE':'1','WINDOW_BITS':str(a.w),'WINDOWED_QROM_UNLOAD':'split','QIP_DIAGNOSTIC_PHASES':'1'}
        if a.w==16:extra['QIP_RESERVE_OPS']='250000000'
        run([str(binary/'build_circuit')],emitted,f'emit-w{a.w}',extra)
        expected=json.loads((record_root/'logs'/f'target-w{a.w}-smoke-canonical.json').read_text())['ops_sha256']
        assert sha(emitted/'ops.bin')==expected,'Compressed stream differs; do not claim reproduction without a decoded comparison'
    elif a.stage=='stats':
        out,_=run([str(binary/'stats_stream'),str(emitted/'ops.bin')],work,f'stats-w{a.w}')
        if variant=='combined' and a.w==16:assert json.loads(out.read_text())==json.loads((ROOT/'emitted-counts.json').read_text())
    elif a.stage=='targeted':
        for fixture in ['zero-slope','smoke']:
            out,_=run([str(binary/'eval_followup'),str(emitted/'ops.bin'),str(work/'fixtures'/f'{fixture}.tsv'),'-'],work,f'target-w{a.w}-{fixture}',{'EVAL_SHARED_SEED':'qip-canonical-reference-targeted-20260909-v1'})
            assert out.read_bytes()==(record_root/'logs'/f'target-w{a.w}-{fixture}-canonical.tsv').read_bytes(),'Targeted outcome mismatch'
    else:
        if variant!='combined' or a.w!=16:raise ValueError('The frozen pilot is combined w=16 only')
        checkpoint=emitted/'fresh-4096'
        if checkpoint.exists():raise FileExistsError('Existing pilot checkpoint')
        run([str(binary/'eval_bounded')],emitted,'pilot',{'WINDOWED_MODE':'1','WINDOW_BITS':'16','WINDOWED_TESTS':'4096','WINDOWED_MAX_ERROR_RATE':'1','EVAL_SHARED_SEED':'qip-canonical-replay-fresh-20260909-v1','EVAL_THREADS':'2','EVAL_CHECKPOINT_DIR':str(checkpoint)})
        expected=ROOT/'emit-window-16/fresh-4096'
        assert ledger(checkpoint/'inputs.tsv','index')==ledger(expected/'inputs.tsv','index')
        actual=ledger(checkpoint/'batches.tsv','batch');stored=ledger(expected/'batches.tsv','batch')
        for x,y in zip(actual,stored):assert {k:v for k,v in x.items() if k!='inputs_end_offset'}=={k:v for k,v in y.items() if k!='inputs_end_offset'}
    print('Completed and compared in scratch space:',work)
if __name__=='__main__':main()
