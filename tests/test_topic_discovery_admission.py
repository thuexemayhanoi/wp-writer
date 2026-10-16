"""Automated topic suggestions are not a bypass around provenance or QA."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from topic_factory import validate_discovery_origin,valid_research_sources

class TopicDiscoveryAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.origin='NTD-deadbeef01234567'
        self.ledger={'proposals':{self.origin:{'taxonomy_key':'electric',
            'title':'Cách kiểm tra pin xe điện'}}}
        self.topic={'topic_id':'NT-000081','origin_id':self.origin,
            'title':'Tìm hiểu pin xe điện','taxonomy_key':'electric'}

    def test_registered_proposal_can_enter_research_queue(self):
        self.assertIsNone(validate_discovery_origin(self.topic,self.ledger,set()))

    def test_unknown_proposal_cannot_claim_research_origin(self):
        self.topic['origin_id']='NTD-not-real'
        with self.assertRaisesRegex(ValueError,'Unknown autonomous'):
            validate_discovery_origin(self.topic,self.ledger,set())

    def test_taxonomy_swap_is_not_silent(self):
        self.topic['taxonomy_key']='legal'
        with self.assertRaisesRegex(ValueError,'Research category'):
            validate_discovery_origin(self.topic,self.ledger,set())

    def test_reusing_proposal_for_second_topic_fails(self):
        with self.assertRaisesRegex(ValueError,'already used'):
            validate_discovery_origin(self.topic,self.ledger,{self.origin})

    def test_legacy_non_discovery_topics_not_modified(self):
        self.topic.pop('origin_id')
        self.assertIsNone(validate_discovery_origin(self.topic,{},set()))

    def test_generated_title_without_web_research_is_not_source_evidence(self):
        self.assertFalse(valid_research_sources({}))
        self.assertFalse(valid_research_sources({'external_sources':[]}))

    def test_https_recent_specific_evidence_is_minimum(self):
        today=dt.date.today().isoformat()
        self.assertTrue(valid_research_sources({'external_sources':[
            {'url':'https://vanban.chinhphu.vn/','checked_at':today,
             'supports':'Chỉ trỏ đến cổng tìm kiếm văn bản, không xác nhận nội dung luật.'}]}))

    def test_http_sources_rejected(self):
        today=dt.date.today().isoformat()
        self.assertFalse(valid_research_sources({'external_sources':[
            {'url':'http://vanban.chinhphu.vn/','checked_at':today,'supports':'A'*35}]}))

    def test_expired_and_future_source_dates_rejected(self):
        old=(dt.date.today()-dt.timedelta(days=400)).isoformat()
        future=(dt.date.today()+dt.timedelta(days=1)).isoformat()
        for date in (old,future):
            with self.subTest(date=date):
                self.assertFalse(valid_research_sources({'external_sources':[
                    {'url':'https://vietnamtourism.gov.vn/','checked_at':date,'supports':'A'*35}]}))

if __name__=='__main__':
    unittest.main()
