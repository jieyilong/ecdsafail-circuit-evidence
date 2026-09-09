"""Run preserved experiment scripts in a new .work copy, never over public records."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','build-tail','tail','guards','build-driver','targeted','tests','reanalyze'])
    p.add_argument('--work-dir',type=Path,default=REPO/'.work/followup-reproduction')
    p.add_argument('--streams-root',type=Path)
    p.add_argument('--n',type=int,default=10000000)
    a=p.parse_args()
    base=REPO/'.work'
    if base.is_symlink():raise ValueError('.work must not be a symlink')
    base.mkdir(exist_ok=True)
    work=a.work_dir.absolute()
    resolved=work.resolve()
    if not resolved.is_relative_to(base.resolve()) or resolved==base.resolve():raise ValueError('Use a new subdirectory under this repository .work/')
    for parent in [work,*work.parents]:
        if parent==REPO:break
        if parent.is_symlink():raise ValueError('Symlinked work paths are not allowed')
    if a.stage=='prepare':
        if work.exists():raise FileExistsError('Prepare requires a new work directory')
        subprocess.run([sys.executable,'-B',str(ROOT/'verify.py')],check=True)
        shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('__pycache__'))
        (work/'prepared.json').write_text(json.dumps({'original_package':str(ROOT),'publication_version':'v1.2.0'})+'\n')
        print(work);return
    if not (work/'prepared.json').is_file():raise RuntimeError('Run prepare first')
    for path in work.rglob('*'):
        if path.is_symlink():raise ValueError('Symlinks inside the work copy are not allowed')
        if path.is_file() and path.relative_to(work).parts[0]!='target' and path.stat().st_nlink>1:
            raise ValueError('Hardlinked work inputs/outputs are not allowed')
    # Scientific records in work are disposable copies; publication paths stay read-only.
    env=dict(os.environ,ECDSAFAIL_EVIDENCE_ROOT=str(REPO))
    if a.stage=='build-tail':
        flags=[]
        if shutil.which('pkg-config'):
            found=subprocess.run(['pkg-config','--cflags','--libs','gmp'],capture_output=True,text=True)
            if found.returncode==0:
                import shlex
                flags=shlex.split(found.stdout)
        if not flags:
            flags=['-lgmp']
            if Path('/opt/homebrew/include/gmp.h').is_file():flags=['-I/opt/homebrew/include','-L/opt/homebrew/lib',*flags]
        command=['cc','-O3','round_tail.c',*flags,'-o','round_tail']
    elif a.stage=='tail':command=[sys.executable,'-B','run_tail.py','--n',str(a.n)]
    elif a.stage=='guards':command=[sys.executable,'-B','run_guards.py','--per-stratum','11112','--evidence-root',str(REPO)]
    elif a.stage=='build-driver':command=['cargo','build','--manifest-path','source/Cargo.toml','--release','--locked','--offline','--bin','eval_followup','--target-dir','target']
    elif a.stage=='targeted':
        if a.streams_root is None:raise ValueError('Supply --streams-root from the experiment 06 rebuild')
        for directory in ['ablation-pingpong-product','mixed1321','original-w4','conservative-w4']:
            for filename in ['ops.bin','phases.tsv']:
                if not (a.streams_root/directory/filename).is_file():raise FileNotFoundError(f'{directory}/{filename}')
        env['TRACE_ALL']='1'
        command=[sys.executable,'-B','run_targeted.py','--streams-root',str(a.streams_root.resolve())]
    elif a.stage=='tests':command=[sys.executable,'-B','test_diagnostics.py']
    else:command=[sys.executable,'-B','analyze_targeted.py']
    subprocess.run(command,cwd=work,env=env,check=True)
    if a.stage=='tail' and a.n==10000000:
        original=json.loads((ROOT/'tail-10000000.json').read_text());new=json.loads((work/'tail-10000000.json').read_text())
        assert {k:v for k,v in new.items() if k!='seconds'}=={k:v for k,v in original.items() if k!='seconds'}
    elif a.stage=='guards':
        old=json.loads((ROOT/'guards-11112.json').read_text());new=json.loads((work/'guards-11112.json').read_text())
        assert {k:v for k,v in new.items() if k!='seconds'}=={k:v for k,v in old.items() if k!='seconds'}
    elif a.stage=='targeted':
        for path in (ROOT/'logs').glob('*'):
            if path.suffix in ['.tsv','.trace']:assert path.read_bytes()==(work/'logs'/path.name).read_bytes(),path.name
    print('Completed in scratch space:',work)
if __name__=='__main__':main()
