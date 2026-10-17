"""begin --ids hands a writer session exactly the researched topics meant for it."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import writer_session
from writer_session import claim


def rows(n=6):
    return [{'topic_id': 'NT-%06d' % i, 'topic_qa_status': 'PLANNED', 'wp_post_id': None} for i in range(1, n + 1)]


class RequestedIdsTests(unittest.TestCase):
    def test_claim_honours_requested_ids_in_registry_order(self):
        slot, registry = claim({'leases': {}, 'submissions': {}}, rows(), 'session-a1',
                               count=2, requested_ids=['NT-000004', 'NT-000005'])
        self.assertEqual(registry['leases'][slot]['topic_ids'], ['NT-000004', 'NT-000005'])

    def test_unclaimable_requested_id_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Requested topics not claimable'):
            claim({'leases': {}, 'submissions': {}}, rows(3), 'session-a1', count=2,
                  requested_ids=['NT-000099'])

    def test_begin_cli_passes_requested_ids_and_widens_count(self):
        captured = {}

        def fake_claim(registry, rows_, session, slot, count, **kwargs):
            captured.update(count=count, **kwargs)
            lease = {'session': session, 'topic_ids': kwargs['requested_ids'],
                     'expires_at': '2999-01-01T00:00:00+00:00'}
            return 'W1', {**registry, 'leases': {'W1': lease}}

        registry = {'leases': {}, 'submissions': {}}
        argv = ['writer-session', 'begin', '--session', 'seodev-w9', '--ids', 'NT-000003,NT-000004', '--count', '1']
        with patch('writer_session.remote_snapshot', return_value=('base', registry, rows())), \
                patch('writer_session.git', return_value=json.dumps({'posts': {}})), \
                patch('writer_session.claim', side_effect=fake_claim), \
                patch('writer_session.RemoteState') as remote, patch('writer_session.save'), \
                patch('subprocess.run') as run, patch.object(sys, 'argv', argv):
            run.return_value.returncode = 1
            run.return_value.stdout = ''
            remote.return_value.persist.return_value = 'abc123'
            writer_session.main()
        self.assertEqual(captured['requested_ids'], ['NT-000003', 'NT-000004'])
        self.assertEqual(captured['count'], 2)


if __name__ == '__main__':
    unittest.main()
