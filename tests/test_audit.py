import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit import read_excel
from common import ROOT

class AuditTests(unittest.TestCase):
    def test_all_sheets_and_baseline(self):
        x=read_excel(ROOT/'data/source/audit-2026-10-16.xlsx')
        self.assertEqual(len(x),9)
        self.assertEqual(len(x['01_URL_Inventory'])-1,159)
        self.assertEqual(len(x['03_Categories'])-1,8)
        self.assertEqual(len(x['04_Topic_Candidates'])-1,80)
        self.assertEqual(x['01_URL_Inventory'][1][0],3861)
    def test_published_counts(self):
        x=read_excel(ROOT/'data/source/audit-2026-10-16.xlsx')['01_URL_Inventory'][1:]
        self.assertEqual(sum(r[1]=='Bài viết' and r[2]=='publish' for r in x),135)
        self.assertEqual(sum(r[1]=='Trang' and r[2]=='publish' for r in x),10)
        self.assertEqual(sum(r[1]=='Sản phẩm' and r[2]=='publish' for r in x),13)

if __name__=='__main__': unittest.main()
