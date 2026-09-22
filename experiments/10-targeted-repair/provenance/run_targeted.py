"""Bounded zero-mask repair experiments. Not a frozen population study."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
SOURCE = WORKSPACE / 'ecdsafail-qip-oral-repairs-20260922'
BIN = SOURCE / 'target/release'
FIXTURES = WORKSPACE / 'ecdsafail-circuit-evidence/experiments/09-canonical-reference/fixtures'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['counts', 'component', 'full'])
    parser.add_argument('--variant', choices=['guarded736', 'guarded768', 'masked', 'masked_chunk', 'masked_coords', 'masked_chunk_coords'], default='masked_chunk_coords')
    parser.add_argument('--width', type=int, default=4, choices=[4,16])
    args = parser.parse_args()
    out = ROOT / 'repair-results' / (args.variant + '-w' + str(args.width))
    out.mkdir(parents=True, exist_ok=True)
    env = {k:v for k,v in os.environ.items() if k in ['HOME','PATH','TMPDIR','LANG']}
    env.update(QIP_PINGPONG_PROFILE='guarded' if args.variant=='guarded736' else 'guarded768', TLM_MSBS='40', CONSTPROP_DISABLE='1', SINGLE_CCX_FANOUT_DISABLE='1', DIALOG_GCD_FOLD_MAJ1='1')
    if args.variant.startswith('masked'): env['QIP_ZERO_PAYLOAD_MASK']='1'
    if 'chunk' in args.variant: env['QIP_EXACT_CHUNK_CARRY']='1'
    if 'coords' in args.variant: env['QIP_CANONICAL_COORDS']='1'
    def run(command, cwd, name, extra=None):
        start=time.monotonic()
        with (out/(name+'.stdout')).open('w') as stdout, (out/(name+'.stderr')).open('w') as stderr:
            r=subprocess.run([str(x) for x in command],cwd=cwd,env=env|dict(extra or {}),stdout=stdout,stderr=stderr,timeout=600)
        (out/(name+'.json')).write_text(json.dumps({'command':[str(x) for x in command],'environment':env|dict(extra or {}),'seconds':time.monotonic()-start,'exit_code':r.returncode},indent=2)+'\n')
        r.check_returncode()
    window={'WINDOWED_MODE':'1','WINDOW_BITS':str(args.width),'WINDOWED_QROM_UNLOAD':'split'}
    if args.stage=='component':
        run([BIN/'build_circuit'],SOURCE,'component',{'QIP_BOUNDARY_MODE':'component'})
        print('\n'.join(x for x in (out/'component.stdout').read_text().splitlines() if x.startswith(('COMPONENT ','PRERESET ','SPLIT_EQ'))))
    elif args.stage=='counts':
        run([BIN/'build_circuit'],out,'counts',window|{'QIP_COUNT_REFERENCE':'1'})
        text=(out/'counts.stderr').read_text()
        print('\n'.join(x for x in text.splitlines() if 'REFERENCE_COUNTS' in x))
    else:
        run([BIN/'build_circuit'],out,'emit',window)
        run([BIN/'stats_stream',out/'ops.bin'],out,'stats')
        print((out/'stats.stdout').read_text())
        for name in ['zero-slope','smoke']:
            run([BIN/'eval_followup',out/'ops.bin',FIXTURES/(name+'.tsv'),'-'],out,name,{'EVAL_SHARED_SEED':'qip-targeted-repair-20260922-v1'})
            print((out/(name+'.stderr')).read_text()[-1500:])

if __name__=='__main__':main()
