"""Structural guard: only privileged paths are assigned to CODEOWNERS.

This is NOT proof that GitHub enforces mandatory review; branch ruleset must
require PRs and Code Owner review before security can be marked verified.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CodeownerScopeTests(unittest.TestCase):
    def test_writer_content_does_not_need_owner_review(self):
        lines=[x.strip() for x in (ROOT/'.github/CODEOWNERS').read_text().splitlines()
               if x.strip() and not x.lstrip().startswith('#')]
        patterns=[line.split()[0] for line in lines]
        self.assertNotIn('*',patterns,'a catchall would require approvals for every AI article')
        for writer_path in ('/posts/drafts/NT-000075.md',
                            '/data/writer-requests/s-agent.json',
                            '/data/topic-research/example.json'):
            for p in patterns:
                self.assertFalse(writer_path==p or (p.endswith('/') and writer_path.startswith(p)),
                                 f'{writer_path} must be unowned: {p}')

    def test_privileged_source_requires_owner(self):
        lines=[x.strip().split() for x in (ROOT/'.github/CODEOWNERS').read_text().splitlines()
               if x.strip() and not x.lstrip().startswith('#')]
        entries={path:who for path,who in lines}
        for p in ('/.github/','/scripts/','/tests/','/config/',
                  '/requirements.txt','/AGENTS.md','/data/state/',
                  '/data/taxonomy.json','/data/topics.jsonl'):
            self.assertEqual(entries.get(p),'@thuexemayhanoi',p)

if __name__=='__main__':
    unittest.main()
