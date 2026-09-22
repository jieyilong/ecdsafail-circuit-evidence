"""Explicit targeted-repair reproduction in .work; archived inputs stay read-only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from common import ROOT, read_json, sha, work_path
from verify_latest import EXPERIMENT, rows

def prepare_safegcd():
    work=work_path('.work/latest-safegcd')
    if work.exists():raise FileExistsError(work)
    source=work/'ecdsafail-qip-safegcd-20260922'
    shutil.copytree(ROOT/'experiments/13-safegcd-reference/source',source)
    shutil.copytree(ROOT/'experiments/13-safegcd-reference/matched-shell-source',source/'matched_reference')
    models=work/'research/qip-oral-20260922/safegcd';models.mkdir(parents=True)
    for name in ['scalar.py','verify.py']:
        shutil.copy2(ROOT/'experiments/13-safegcd-reference'/name,models/name)
    print(work)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','build','cells','emit','targeted','study','prepare-safegcd'])
    p.add_argument('--width',type=int,choices=[4,16],default=16)
    p.add_argument('--stratum',type=int,choices=range(9),default=0)
    p.add_argument('--work-dir',default='.work/latest-targeted-repair')
    p.add_argument('--offline',action='store_true')
    a=p.parse_args()
    if a.stage=='prepare-safegcd':return prepare_safegcd()
    work=work_path(a.work_dir)
    if a.stage=='prepare':
        if work.exists():raise FileExistsError(work)
        freeze=read_json(EXPERIMENT/'fresh-study/freeze.json')
        for name,h in freeze['source'].items():assert sha(EXPERIMENT/'source'/name)==h
        shutil.copytree(EXPERIMENT/'source',work/'source')
        (work/'logs').mkdir()
        print(work);return
    if not (work/'source/Cargo.toml').is_file():raise RuntimeError('Run prepare first')
    env={k:v for k,v in os.environ.items() if k in ['HOME','PATH','TMPDIR','LANG','CARGO_HOME']}
    env.update(QIP_PINGPONG_PROFILE='guarded768',QIP_ZERO_PAYLOAD_MASK='1',QIP_EXACT_CHUNK_CARRY='1',QIP_CANONICAL_COORDS='1',
        TLM_MSBS='40',CONSTPROP_DISABLE='1',SINGLE_CCX_FANOUT_DISABLE='1',DIALOG_GCD_FOLD_MAJ1='1')
    binary=work/'target/release';emitted=work/f'emit-w{a.width}'
    def run(command,cwd,name,extra=None):
        log=work/'logs'/name
        if log.with_suffix('.stdout').exists():raise FileExistsError('Existing run log; choose a fresh work directory')
        start=time.monotonic()
        with log.with_suffix('.stdout').open('w') as out,log.with_suffix('.stderr').open('w') as err:
            result=subprocess.run([str(x) for x in command],cwd=cwd,env=env|dict(extra or {}),stdout=out,stderr=err,timeout=3600)
        log.with_suffix('.json').write_text(json.dumps({'exit_code':result.returncode,'seconds':time.monotonic()-start,'command':[str(x) for x in command]},indent=2)+'\n')
        result.check_returncode();return log.with_suffix('.stdout')
    if a.stage=='build':
        command=['cargo','build','--release','--locked','--manifest-path','source/Cargo.toml','--target-dir','target','-j','2']
        if a.offline:command.append('--offline')
        for name in ['build_circuit','eval_bounded','eval_followup','stats_stream']:command+=['--bin',name]
        run(command,work,'build')
    elif a.stage=='cells':
        output=run([binary/'build_circuit'],work/'source','cells',{'QIP_BOUNDARY_MODE':'cells'})
        print('Raw generic-cell outcomes include retained failures:',output)
    elif a.stage=='emit':
        emitted.mkdir()
        run([binary/'build_circuit'],emitted,f'emit-w{a.width}',{'WINDOWED_MODE':'1','WINDOW_BITS':str(a.width),'WINDOWED_QROM_UNLOAD':'split'})
        stats=run([binary/'stats_stream',emitted/'ops.bin'],work,f'stats-w{a.width}')
        expected=read_json(EXPERIMENT/f'diagnostics/masked_chunk_coords-w{a.width}/stats.stdout')
        assert read_json(stats)==expected,'Serialized counts differ'
        if a.width==16:assert sha(emitted/'ops.bin')==read_json(EXPERIMENT/'fresh-study/freeze.json')['ops_sha256'],'Stream identity differs'
    elif a.stage=='targeted':
        for name in ['zero-slope','smoke']:
            fixture=ROOT/'experiments/09-canonical-reference/fixtures'/f'{name}.tsv'
            output=run([binary/'eval_followup',emitted/'ops.bin',fixture,'-'],work,f'{name}-w{a.width}',{'EVAL_SHARED_SEED':'qip-targeted-repair-20260922-v1'})
            assert rows(output)==rows(EXPERIMENT/f'diagnostics/masked_chunk_coords-w{a.width}'/f'{name}.stdout')
    else:
        if a.width!=16:raise ValueError('Frozen study uses w=16')
        spec=read_json(EXPERIMENT/'fresh-study/plan.json')['strata'][a.stratum]
        checkpoint=work/f'stratum-{a.stratum}'
        run([binary/'eval_bounded'],emitted,f'study-{a.stratum}',{'WINDOWED_MODE':'1','WINDOW_BITS':'16','WINDOWED_TESTS':str(spec['n']),
            'WINDOWED_MAX_ERROR_RATE':'1','EVAL_THREADS':'2','EVAL_SHARED_SEED':spec['seed'],'QIP_TABLE_BETA':spec['beta'],'EVAL_CHECKPOINT_DIR':str(checkpoint)})
        expected=EXPERIMENT/f'fresh-study/stratum-{a.stratum}/checkpoint'
        keyed=lambda xs,key:{int(x[key]):x for x in xs}
        assert keyed(rows(checkpoint/'inputs.tsv'),'index')==keyed(rows(expected/'inputs.tsv.gz'),'index')
        normalized=lambda xs:{int(x['batch']):{k:v for k,v in x.items() if k!='inputs_end_offset'} for x in xs}
        assert normalized(rows(checkpoint/'batches.tsv'))==normalized(rows(expected/'batches.tsv'))
    print('PASS:',a.stage,work)

if __name__=='__main__':main()
