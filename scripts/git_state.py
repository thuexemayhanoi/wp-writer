"""Git compare-and-swap commits, preserving unrelated writer changes."""
import os
import subprocess
import tempfile
from pathlib import Path
from common import ROOT, git

class RemoteState:
    def __init__(self):
        self.expected={}

    def remember(self, paths):
        base=git('rev-parse','HEAD')
        for path in paths:
            p=subprocess.run(['git','rev-parse',base+':'+path],cwd=ROOT,text=True,capture_output=True)
            self.expected[path]=p.stdout.strip() if p.returncode==0 else None

    def persist(self, paths, message='chore: factory durable checkpoint [skip ci]'):
        paths=list(paths)
        for attempt in range(4):
            git('fetch','origin','main');base=git('rev-parse','origin/main')
            for path in paths:
                p=subprocess.run(['git','rev-parse',base+':'+path],cwd=ROOT,text=True,capture_output=True)
                current=p.stdout.strip() if p.returncode==0 else None
                if current!=self.expected.get(path): raise RuntimeError('State conflict; reconcile before another WordPress write: '+path)
            blobs={path:git('hash-object','-w',str(ROOT/path)) for path in paths}
            if all(blobs[p]==self.expected.get(p) for p in paths): return base
            with tempfile.TemporaryDirectory() as tmp:
                env={**os.environ,'GIT_INDEX_FILE':str(Path(tmp)/'index')}
                git('read-tree',base,env=env)
                for path,blob in blobs.items():git('update-index','--add','--cacheinfo',f'100644,{blob},{path}',env=env)
                tree=git('write-tree',env=env)
                commit=git('commit-tree',tree,'-p',base,input=message+'\n')
            p=subprocess.run(['git','push','origin',commit+':refs/heads/main'],cwd=ROOT,text=True,capture_output=True)
            if p.returncode==0:
                self.expected.update(blobs);return commit
        raise RuntimeError('Remote checkpoint push failed; no WordPress POST allowed')
