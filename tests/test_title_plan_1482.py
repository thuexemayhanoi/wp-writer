"""Read-only structural/SEO safeguards for the 1482-title planning queue."""
import json
import sys
import unittest
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from title_plan_1482 import norm, GROUPS, CATALOG, TARGET, SPLIT

class TitlePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=ROOT/'editorial'/'title-plan-1482'
        cls.base=base
        cls.data=json.loads((base/'plan.json').read_text(encoding='utf-8'))
        cls.rows=cls.data['rows']
        cls.baseline=json.loads((base/'baseline-518.json').read_text(encoding='utf-8'))
    def test_count_and_exact_category_distribution(self):
        self.assertEqual(len(self.rows),TARGET)
        self.assertEqual(len(GROUPS),18)
        counts=Counter(x['category_id'] for x in self.rows)
        self.assertEqual(set(counts),set(GROUPS))
        self.assertEqual(set(counts.values()),{82,83})
        self.assertEqual(sum(counts.values()),1482)
        for x in self.rows:
            self.assertEqual((x['taxonomy_key'],x['parent']),CATALOG[x['category_id']])
    def test_true_518_live_baseline_and_no_head_keyword_cannibalization(self):
        self.assertEqual(self.baseline['total'],518)
        self.assertEqual(len(self.baseline['posts']),518)
        original={norm(x['title']) for x in self.baseline['posts']}
        titles=[norm(x['title']) for x in self.rows]
        self.assertEqual(len(set(titles)),1482)
        self.assertFalse(set(titles)&original)
        self.assertFalse(any('thue xe may ha noi' in x for x in titles))
        self.assertTrue(all(60<=len(x['title'])<=80 for x in self.rows))
    def test_ids_are_stable_and_initially_unclaimed(self):
        self.assertEqual([x['plan_id'] for x in self.rows],
                         ['TP-%04d'%i for i in range(1,1483)])
        for x in self.rows:
            self.assertEqual(x['sources_min'],1)
            self.assertEqual(x['sources_max'],4)
            self.assertIn(x['status'],{'PLANNED','RESEARCHING',
              'WRITER_QA','QA_REVIEW','PUBLISHED_G7_PASS','EXTERNAL_REVIEW'})
    def test_spreadsheets_contain_full_rows_and_valid_openxml(self):
        for part in (1,2,3):
            name=f'seo-tieu-de-{part:02d}-494'
            xlsx=self.base/(name+'.xlsx')
            self.assertTrue(xlsx.is_file())
            with zipfile.ZipFile(xlsx) as zf:
                self.assertIsNone(zf.testzip())
                names=set(zf.namelist())
                self.assertIn('xl/styles.xml',names)
                self.assertIn('xl/worksheets/sheet1.xml',names)
                tree=ET.fromstring(zf.read('xl/worksheets/sheet1.xml'))
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                self.assertEqual(len(tree.findall('.//s:sheetData/s:row',ns)),495)
                self.assertEqual(len(tree.findall('.//s:autoFilter',ns)),1)
                self.assertEqual(len(tree.findall('.//s:pane',ns)),1)
            self.assertGreater(xlsx.stat().st_size,15000)

if __name__=='__main__':
    unittest.main()
