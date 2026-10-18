"""Local bare repository tests: genuine git CAS, no GitHub or WordPress."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import common
import git_state

class BareRepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.bare=self.base/'remote.git';self.repo=self.base/'checkout'
        self.cmd('git','init','--bare','--initial-branch=main',str(self.bare))
        self.cmd('git','clone',str(self.bare),str(self.repo))
        self.cmd('git','config','user.name','Test',cwd=self.repo);self.cmd('git','config','user.email','test@example.invalid',cwd=self.repo)
        (self.repo/'state.json').write_text('{}');self.cmd('git','add','.',cwd=self.repo);self.cmd('git','commit','-m','seed',cwd=self.repo);self.cmd('git','push','origin','main',cwd=self.repo)
    def tearDown(self):self.tmp.cleanup()
    def cmd(self,*args,**kwargs):return subprocess.check_output(args,stderr=subprocess.DEVNULL,text=True,**kwargs).strip()

class GitCASTests(BareRepoCase):
    def test_stale_writer_cannot_replace_new_checkpoint(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            first=git_state.RemoteState();second=git_state.RemoteState();first.remember(['state.json']);second.remember(['state.json'])
            (self.repo/'state.json').write_text('{"owner":"first"}');first.persist(['state.json'])
            (self.repo/'state.json').write_text('{"owner":"second"}')
            with self.assertRaises(RuntimeError):second.persist(['state.json'])
            self.assertIn('first',self.cmd('git','show','origin/main:state.json',cwd=self.repo))
    def test_publisher_preserves_unrelated_content_push(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            state=git_state.RemoteState();state.remember(['state.json'])
            (self.repo/'writer.md').write_text('owned draft')
            self.cmd('git','add','writer.md',cwd=self.repo);self.cmd('git','commit','-m','writer',cwd=self.repo);self.cmd('git','push','origin','main',cwd=self.repo)
            (self.repo/'state.json').write_text('{"phase":"POST_INTENT"}');state.persist(['state.json'])
            self.assertEqual(self.cmd('git','show','origin/main:writer.md',cwd=self.repo),'owned draft')
            self.assertIn('POST_INTENT',self.cmd('git','show','origin/main:state.json',cwd=self.repo))

class PathLevelCASTests(BareRepoCase):
    """CAS is per path: only a file this process rewrote can conflict."""
    def setUp(self):
        super().setUp()
        (self.repo/'report.json').write_text('{"v":1}')
        self.cmd('git','add','.',cwd=self.repo);self.cmd('git','commit','-m','report',cwd=self.repo);self.cmd('git','push','origin','main',cwd=self.repo)
    def newer_report_elsewhere(self):
        other=self.base/'other'
        self.cmd('git','clone',str(self.bare),str(other))
        self.cmd('git','config','user.name','Other',cwd=other);self.cmd('git','config','user.email','o@example.invalid',cwd=other)
        (other/'report.json').write_text('{"v":"newer"}')
        self.cmd('git','commit','-am','newer report',cwd=other);self.cmd('git','push','origin','main',cwd=other)
    def shown(self,path):return self.cmd('git','show','origin/main:'+path,cwd=self.repo)
    def test_a_path_this_process_did_not_change_never_conflicts(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            state=git_state.RemoteState();state.remember(['state.json','report.json'])
            self.newer_report_elsewhere()
            (self.repo/'state.json').write_text('{"phase":"X"}')
            state.persist(['state.json','report.json'])
            self.assertIn('"X"',self.shown('state.json'))
            self.assertIn('newer',self.shown('report.json'))  # the other commit survives untouched
    def test_nothing_changed_here_means_nothing_is_pushed(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            state=git_state.RemoteState();state.remember(['state.json','report.json'])
            self.newer_report_elsewhere()
            head=self.cmd('git','ls-remote','origin','refs/heads/main',cwd=self.repo).split()[0]
            self.assertEqual(state.persist(['state.json','report.json']),head)
            self.assertEqual(self.cmd('git','ls-remote','origin','refs/heads/main',cwd=self.repo).split()[0],head)
    def test_a_path_this_process_changed_still_conflicts_and_nothing_is_pushed(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            state=git_state.RemoteState();state.remember(['state.json','report.json'])
            self.newer_report_elsewhere()
            (self.repo/'state.json').write_text('{"phase":"X"}');(self.repo/'report.json').write_text('{"v":"stale"}')
            with self.assertRaisesRegex(RuntimeError,'report.json'):state.persist(['state.json','report.json'])
            self.assertEqual(self.shown('state.json'),'{}')  # all or nothing for the paths that did change
    def test_skip_conflicts_drops_only_the_conflicting_derived_path(self):
        with patch.object(common,'ROOT',self.repo),patch.object(git_state,'ROOT',self.repo):
            state=git_state.RemoteState();state.remember(['state.json','report.json'])
            self.newer_report_elsewhere()
            (self.repo/'state.json').write_text('{"phase":"X"}');(self.repo/'report.json').write_text('{"v":"stale"}')
            state.persist(['state.json','report.json'],skip_conflicts=True)
            self.assertEqual(state.skipped,['report.json'])
            self.assertIn('"X"',self.shown('state.json'))
            self.assertIn('newer',self.shown('report.json'))

if __name__=='__main__':unittest.main()
