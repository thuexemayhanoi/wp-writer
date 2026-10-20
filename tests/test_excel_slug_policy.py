"""Regressions: Excel is source metadata, never a public WordPress URL segment."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from slug_policy import suggested_slug, proposed_slug_errors
from common import SITE
from topic_factory import gate


class ExcelSlugPolicyTests(unittest.TestCase):
    def topic(self, slug, **updates):
        return {
            'topic_id':'NT-199995',
            'title':'Đổi mẫu xe khi nhận: các tình huống thường gặp và cách trao đổi với cửa hàng',
            'title_plan_id':'TP-0001',
            'proposed_slug':slug,
            'canonical_target':SITE+'/'+slug+'/',
            'taxonomy_key':'rental-procedures',
            'primary_keyword':'đổi mẫu xe khi nhận',
            'search_intent':'hướng dẫn',
            'topic_qa_status':'RESEARCH',
            'outline':['1','2','3','4','5'],
            'research':{},
            **updates
        }

    def test_correct_slug_comes_from_title_without_excel(self):
        t=self.topic('doi-mau-xe-khi-nhan-cac-tinh-huong-thuong-gap')
        self.assertEqual(proposed_slug_errors(t),[])
        suggested=suggested_slug(t['title'])
        self.assertTrue(suggested.startswith('doi-mau-xe-khi-nhan'))
        self.assertNotIn('excel',suggested)
        self.assertLessEqual(len(suggested),96)

    def test_metadata_leak_rejected_even_if_canonical_is_consistent(self):
        for slug in (
                'excel-doi-mau-xe-khi-nhan',
                'doi-mau-xe-khi-nhan-tu-excel',
                'doi-mau-xe-khi-nhan-xlsx',
                'file-excel-tp-0001-doi-mau-xe',
                'seo-tieu-de-01-494-doi-mau-xe',
                'tp-0001-doi-mau-xe-khi-nhan',
        ):
            with self.subTest(slug=slug):
                self.assertTrue(proposed_slug_errors(self.topic(slug)))

    def test_non_plan_legacy_permalink_is_not_mutated(self):
        old=self.topic('cong-cu-excel-tinh-gia',title_plan_id=None,
            title='Công cụ Excel tính giá')
        self.assertEqual(proposed_slug_errors(old),[])
        self.assertEqual(old['proposed_slug'],'cong-cu-excel-tinh-gia')

    def test_legacy_spreadsheet_leak_without_excel_article_title_rejected(self):
        t=self.topic('tu-file-excel-doi-mau-xe',title_plan_id=None)
        self.assertTrue(proposed_slug_errors(t))

    def test_invalid_plan_id_format_rejected(self):
        self.assertTrue(proposed_slug_errors(self.topic('doi-mau-xe-khi-nhan',
                                                        title_plan_id='excel-TP-0001')))

    def test_topic_factory_research_gate_fails_before_acceptance(self):
        t=self.topic('excel-doi-mau-xe-khi-nhan')
        tax=[{'taxonomy_key':'rental-procedures'}]
        verdict=gate(t,[t],[],tax)
        self.assertEqual(verdict['status'],'FAIL')
        self.assertTrue(any('SLUG_SOURCE_FILE_LEAK' in e for e in verdict['errors']))
        self.assertTrue(any('canonical' not in e for e in verdict['errors']))


if __name__=='__main__':
    unittest.main()
