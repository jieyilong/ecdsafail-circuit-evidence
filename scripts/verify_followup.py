"""Verify v1.2 follow-up additions and preserve the v1.1 scientific record."""
import json
import subprocess
import sys
from common import ROOT, read_json, safe_path, sha

def verify_followup():
    old=read_json(ROOT/'provenance/v1.1.0-publication-manifest.json')['files']
    science={k:v for k,v in old.items() if k.startswith(('experiments/','sources/','provenance/','supporting/')) and k!='provenance/publication-manifest.json'}
    for rel,digest in science.items():assert sha(safe_path(ROOT,rel))==digest,rel
    result=subprocess.run([sys.executable,'-B',str(ROOT/'experiments/08-followup-diagnostics/verify.py')],check=True,capture_output=True,text=True)
    record=json.loads(result.stdout);assert record['status']=='PASS'
    record['preserved_v11_scientific_files']=len(science)
    return record
if __name__=='__main__':print(json.dumps(verify_followup(),indent=2))
