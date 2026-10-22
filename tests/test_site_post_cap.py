"""Owner hard ceiling on public WordPress posts (`site_published_post_cap`): pure helpers, no WordPress access."""
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publisher import count_site_posts,site_cap_reached


class SitePostCapTests(unittest.TestCase):
    def test_only_public_posts_count(self):
        live=[{'resource':'posts','status':'publish'},{'resource':'posts','status':'publish'},
              {'resource':'posts','status':'draft'},{'resource':'posts','status':'private'},
              {'resource':'pages','status':'publish'}]
        self.assertEqual(count_site_posts(live),2)

    def test_cap_stops_exactly_at_the_limit(self):
        self.assertFalse(site_cap_reached(999,1000))
        self.assertTrue(site_cap_reached(1000,1000))
        self.assertTrue(site_cap_reached(1001,1000))

    def test_unset_or_zero_cap_is_disabled(self):
        self.assertFalse(site_cap_reached(5000,None))
        self.assertFalse(site_cap_reached(5000,0))

    def test_in_run_counter_never_allows_the_1001st_post(self):
        site_posts=996;created=0
        for _ in range(10):
            if site_cap_reached(site_posts,1000):break
            site_posts+=1;created+=1
        self.assertEqual(created,4)
        self.assertEqual(site_posts,1000)

    def test_policy_ceiling_is_a_positive_integer_when_present(self):
        policy=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        cap=policy.get('site_published_post_cap')
        if cap is not None:
            self.assertIs(type(cap),int)
            self.assertGreater(cap,0)


class OwnerPauseStopsTopicAutomationTests(unittest.TestCase):
    def test_research_intake_main_is_idle_while_paused(self):
        import io,contextlib
        import research_intake as intake
        buf=io.StringIO()
        with unittest.mock.patch.object(intake,'owner_paused',return_value=True),\
             unittest.mock.patch.object(sys,'argv',['research_intake.py','--sweep']),\
             contextlib.redirect_stdout(buf):
            intake.main()
        self.assertEqual(json.loads(buf.getvalue())['status'],'PAUSED')

    def test_owner_paused_reads_both_switches(self):
        import research_intake as intake
        for policy,expected in (({'paused':True},True),({'emergency_stop':True},True),({'paused':False,'emergency_stop':False},False)):
            with unittest.mock.patch.object(intake,'load',return_value=policy):
                self.assertIs(intake.owner_paused(),expected)


if __name__=='__main__':
    unittest.main()
