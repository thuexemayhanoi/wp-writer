"""CAS-persist generated reports; never blind rebase state."""
import subprocess
from common import ROOT
from git_state import RemoteState

if __name__=='__main__':
    paths=[str(p.relative_to(ROOT)) for p in (ROOT/'reports').glob('*') if p.is_file()]
    paths += [str(p.relative_to(ROOT)) for p in (ROOT/'data/qa').glob('*.json')]
    paths += ['data/state/checkpoint.json']
    state=RemoteState();state.remember(paths);state.persist(paths)
