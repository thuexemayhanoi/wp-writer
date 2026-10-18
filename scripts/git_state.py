"""Git compare-and-swap commits, preserving unrelated writer changes."""
import os
import subprocess
import tempfile
from pathlib import Path
from common import ROOT, git

class RemoteState:
    def __init__(self):
        self.expected={}
        self.skipped=[]

    def remember(self, paths):
        base=git('rev-parse','HEAD')
        for path in paths:
            p=subprocess.run(['git','rev-parse',base+':'+path],cwd=ROOT,text=True,capture_output=True)
            self.expected[path]=p.stdout.strip() if p.returncode==0 else None

    def persist(self, paths, message='chore: factory durable checkpoint [skip ci]', skip_conflicts=False):
        """Commit the paths this process changed to main and keep everything other commits did meanwhile.

        Compare-and-swap is per path. A path whose local content is still what `remember` recorded was not changed
        here: it is never written, so another commit to it is not a conflict (a publisher run that merely regenerates
        reports must not fail because intake rewrote reports/topic-qa.json while it ran). A path this process did
        change must still match the remembered base on origin/main, otherwise a stale writer would overwrite newer
        state: that raises, or, with skip_conflicts (derived reports that the next run regenerates), drops only
        that path and lists it in `self.skipped`.
        """
        paths=list(paths)
        blobs={path:git('hash-object','-w',str(ROOT/path)) for path in paths}
        mine=[path for path in paths if blobs[path]!=self.expected.get(path)]
        for attempt in range(4):
            git('fetch','origin','main');base=git('rev-parse','origin/main')
            keep=[];self.skipped=[]
            for path in mine:
                p=subprocess.run(['git','rev-parse',base+':'+path],cwd=ROOT,text=True,capture_output=True)
                current=p.stdout.strip() if p.returncode==0 else None
                if current!=self.expected.get(path):
                    if not skip_conflicts: raise RuntimeError('State conflict; reconcile before another WordPress write: '+path)
                    self.skipped.append(path)
                else: keep.append(path)
            if not keep: return base
            with tempfile.TemporaryDirectory() as tmp:
                env={**os.environ,'GIT_INDEX_FILE':str(Path(tmp)/'index')}
                git('read-tree',base,env=env)
                for path in keep:git('update-index','--add','--cacheinfo',f'100644,{blobs[path]},{path}',env=env)
                tree=git('write-tree',env=env)
                commit=git('commit-tree',tree,'-p',base,input=message+'\n')
            p=subprocess.run(['git','push','origin',commit+':refs/heads/main'],cwd=ROOT,text=True,capture_output=True)
            if p.returncode==0:
                self.expected.update({path:blobs[path] for path in keep});return commit
        raise RuntimeError('Remote checkpoint push failed; no WordPress POST allowed')


# Opt-in storage adapter. Existing production and Writer callers intentionally
# keep using RemoteState(main) until branch protection + reader migration is
# independently verified; the adapter is NOT an automatic production switch.
STATE_REF = "factory-state"
STATE_PATH_PREFIXES = ("data/state/", "data/qa/", "reports/")
STATE_EXACT_PATHS = frozenset(())


def _validate_state_paths(paths):
    """Fail closed: factory-state never accepts code, topics, taxonomy or posts."""
    import re
    paths = list(paths)
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Empty/duplicate factory-state CAS path list")
    for path in paths:
        if not isinstance(path, str) or not re.fullmatch(
            r"(?:data/state/[a-z0-9][a-z0-9_-]*\.json|"
            r"data/qa/NT-[0-9]{6}\.json|"
            r"reports/[a-zA-Z0-9][a-zA-Z0-9_.-]*\.(?:json|csv|md))", path
        ):
            raise ValueError("FORBIDDEN_FACTORY_STATE_PATH: " + str(path)[:120])
    return paths


class FactoryStateCAS:
    """Branch-isolated CAS for approved state/report paths only.

    Crucial: ONLY a trusted main GitHub workflow should invoke persist().
    GitHub Ruleset must separately restrict who may push to factory-state.
    The caller must read its state from this SAME branch after cutover.
    Never use this as a drop-in replacement for a mixed content+state commit.
    """
    def __init__(self):
        self.expected = {}

    @staticmethod
    def _snapshot():
        git("fetch", "--no-tags", "origin",
            "refs/heads/" + STATE_REF + ":refs/remotes/origin/" + STATE_REF)
        return git("rev-parse", "refs/remotes/origin/" + STATE_REF)

    @staticmethod
    def _blob_at(commit, path):
        check = subprocess.run(
            ["git", "rev-parse", commit + ":" + path], cwd=ROOT,
            text=True, capture_output=True)
        return check.stdout.strip() if check.returncode == 0 else None

    def remember(self, paths):
        paths = _validate_state_paths(paths)
        base = self._snapshot()
        self.expected = {path: self._blob_at(base, path) for path in paths}
        return base

    def read_bytes(self, path):
        _validate_state_paths([path])
        base = self._snapshot()
        p = subprocess.run(["git", "show", base + ":" + path], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode:
            raise FileNotFoundError("Factory-state record absent: " + path)
        return p.stdout

    def persist(self, paths, message="chore: isolated factory-state checkpoint [skip ci]"):
        paths = _validate_state_paths(paths)
        if any(path not in self.expected for path in paths):
            raise RuntimeError("CAS remember() required before state commit")
        blobs = {}
        for path in paths:
            file = ROOT / path
            if not file.is_file() or file.is_symlink():
                raise ValueError("Missing/unsafe factory-state record: " + path)
            blobs[path] = git("hash-object", "-w", str(file))
        for attempt in range(4):
            base = self._snapshot()
            for path in paths:
                if self._blob_at(base, path) != self.expected[path]:
                    raise RuntimeError(
                        "Factory-state CAS CONFLICT; reconcile before WordPress POST: " + path
                    )
            if all(blobs[p] == self.expected[p] for p in paths):
                return base
            with tempfile.TemporaryDirectory() as tmp:
                env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
                git("read-tree", base, env=env)
                for path, blob in blobs.items():
                    git("update-index", "--add", "--cacheinfo",
                        f"100644,{blob},{path}", env=env)
                tree = git("write-tree", env=env)
                commit = git("commit-tree", tree, "-p", base,
                             input=message + "\n")
            p = subprocess.run(
                ["git", "push", "origin", commit + ":refs/heads/" + STATE_REF],
                cwd=ROOT, text=True, capture_output=True
            )
            if p.returncode == 0:
                self.expected.update(blobs)
                return commit
        raise RuntimeError("Factory-state push failed; no WordPress POST allowed")
