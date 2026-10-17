"""CAS-persist only authenticated audit artifacts; never rebase Writer content.

Called AFTER scripts/audit.py --authenticated. A concurrent Owner/Writer update
to any of these paths causes a conflict instead of overwriting it.
No WordPress access or secret is needed to persist already-read audit files.
"""
from pathlib import Path

from common import ROOT
from git_state import RemoteState

AUDIT_PATHS = (
    "data/existing-content-inventory.json",
    "data/existing-taxonomy.json",
    "data/protected-urls.json",
    "reports/audit.json",
)


def run():
    for relative in AUDIT_PATHS:
        path = ROOT / relative
        if not path.is_file() or not path.read_bytes():
            raise RuntimeError("Missing/empty authenticated audit output: " + relative)
    state = RemoteState()
    state.remember(AUDIT_PATHS)
    commit = state.persist(AUDIT_PATHS,
                           "chore: CAS refresh authenticated factory inventory [skip ci]")
    print("AUDIT_CAS_OK: " + commit + "; preserved unrelated Writer and state changes")
    return commit


if __name__ == "__main__":
    run()
