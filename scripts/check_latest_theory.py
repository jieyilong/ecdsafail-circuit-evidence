"""Portable read-only execution of the new mathematical regression checks."""
import argparse
import importlib.util
import json
import sys
from common import ROOT

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule-only',action='store_true');a=p.parse_args()
    if a.schedule_only:
        model=module(ROOT/'experiments/12-schedule-audit/model.py','schedule_model')
        records={str(d):model.walk(d,limit=4096) for d in [1,3,2**255]}
        assert records['1']['first_terminal_round']==512
        assert records['1']['misses']['candidate768']['k']==177
        assert records['3']['first_terminal_round']==1135
        assert records[str(2**255)]['first_terminal_round']==1239
        print(json.dumps({'status':'PASS','terminal_rounds':{k:v['first_terminal_round'] for k,v in records.items()},'width_miss_d1':177},indent=2))
        return
    folder=ROOT/'experiments/11-coherent-error'
    matrix=module(folder/'matrix_checks.py','matrix_checks')
    prefixes=module(folder/'prefix_support.py','prefix_support')
    result={'matrix':matrix.run(),'prefixes':prefixes.run()}
    print(json.dumps({'status':'PASS','matrix_trials':result['matrix']['random_reference_entangled_isometries']['trials'],
                     'curve_pairs':result['prefixes']['small_curve_exhaustive']['all_curve_pair_checks']},indent=2))

if __name__=='__main__':main()
