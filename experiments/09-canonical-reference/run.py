"""Bounded canonical-replay experiment runner. No frozen artifacts are modified."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['cells','component','emit','count','random']);parser.add_argument('--w',type=int,default=4);parser.add_argument('--n',type=int,default=1024);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
    binary=ROOT/'target/release/build_circuit'
    env={k:v for k,v in os.environ.items() if not k.startswith(('QIP_','TLM_','SUB4_','DIALOG_','KAL_','WINDOW','EVAL_','CONSTPROP_','SINGLE_CCX_','TRACE_'))}
    env.update(QIP_PINGPONG_PROFILE='guarded',TLM_MSBS='40',CONSTPROP_DISABLE='1',SINGLE_CCX_FANOUT_DISABLE='1')
    if args.mode=='emit':env['QIP_DIAGNOSTIC_PHASES']='1'
    if not args.baseline:env.update(QIP_CANONICAL_REPLAY='1',QIP_CANONICAL_COORDS='1')
    tag=f'{args.mode}-w{args.w}-n{args.n}-'+('baseline' if args.baseline else 'canonical')
    cwd=ROOT/'source'
    if args.mode in ['cells','component']:env['QIP_BOUNDARY_MODE']=args.mode
    elif args.mode in ['emit','count']:
        env.update(WINDOWED_MODE='1',WINDOW_BITS=str(args.w),WINDOWED_QROM_UNLOAD='split')
        cwd=ROOT/f'{args.mode}-window-{args.w}';cwd.mkdir(exist_ok=True)
        if args.mode=='count':env['QIP_COUNT_REFERENCE']='1'
    elif args.mode=='random':
        binary=ROOT/'target/release/eval_bounded';cwd=ROOT/f'emit-window-{args.w}'
        checkpoint=cwd/f'fresh-{args.n}'; assert not checkpoint.exists()
        env.update(WINDOWED_MODE='1',WINDOW_BITS=str(args.w),WINDOWED_TESTS=str(args.n),WINDOWED_MAX_ERROR_RATE='1',EVAL_SHARED_SEED='qip-canonical-replay-fresh-20260909-v1',EVAL_THREADS='2',EVAL_CHECKPOINT_DIR=str(checkpoint))
    if args.mode=='emit' and args.w==16:env['QIP_RESERVE_OPS']='250000000'
    # Fail before launching a large child if the RSS watchdog cannot inspect it.
    subprocess.run(['ps','-o','rss=','-p',str(os.getpid())],capture_output=True,check=True)
    start=time.time()
    with (ROOT/'logs'/f'{tag}.log').open('w') as f:
        run=subprocess.Popen([str(binary)],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        peak_kib=0
        try:
            while run.poll() is None:
                rss=subprocess.run(['ps','-o','rss=','-p',str(run.pid)],capture_output=True,text=True)
                if rss.returncode==0 and rss.stdout.strip():peak_kib=max(peak_kib,int(rss.stdout.strip()))
                if peak_kib>19_000_000 or time.time()-start>1200:
                    raise RuntimeError('RSS/time budget exceeded')
                time.sleep(.5)
        finally:
            if run.poll() is None:run.kill();run.wait()
    record={'mode':args.mode,'command':[str(binary)],'cwd':str(cwd),'env':{k:v for k,v in env.items() if k.startswith(('QIP_','TLM_','WINDOW','EVAL_','CONSTPROP','SINGLE'))},'exit_code':run.returncode,'seconds':time.time()-start,'sampled_peak_kib':peak_kib,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':{str(p.relative_to(ROOT/'source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'source/src').rglob('*.rs'))}}
    (ROOT/'logs'/f'{tag}.json').write_text(json.dumps(record,indent=2)+'\n')
    print(tag,run.returncode,round(record['seconds'],2));assert run.returncode==0
if __name__=='__main__':main()
