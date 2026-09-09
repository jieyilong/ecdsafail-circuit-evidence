"""Verify the separate v1.3 correctness reference and preserve prior science."""
import json
import subprocess
import sys
from common import ROOT,read_json,safe_path,sha
def verify_reference():
    old=read_json(ROOT/'provenance/v1.2.0-publication-manifest.json')['files']
    science={k:v for k,v in old.items() if k.startswith(('experiments/','sources/','provenance/','supporting/')) and k!='provenance/publication-manifest.json'}
    for name,digest in science.items():assert sha(safe_path(ROOT,name))==digest,name
    result=subprocess.run([sys.executable,'-B',str(ROOT/'experiments/09-canonical-reference/verify.py')],check=True,capture_output=True,text=True)
    report=json.loads(result.stdout);assert report['status']=='PASS'
    report['preserved_v12_scientific_files']=len(science)
    return report
if __name__=='__main__':print(json.dumps(verify_reference(),indent=2))
