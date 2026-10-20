"""Regression checks for real Nguyen Tu model-specific rental rates.

The first three Hanoi ward articles now place distinct model prices on
unambiguous lines. Keep the safety validator strict about genuinely wrong
rates while accepting accurate per-model claims.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from qa import business_errors


class HanoiWardPriceClaimTests(unittest.TestCase):
    def test_verified_model_rates_on_distinct_lines(self):
        article = (
            "Thuê Honda Wave giá tham khảo 150.000 đồng/ngày.\n"
            "Thuê Honda Vision giá tham khảo 200.000 đồng/ngày.\n"
            "Thuê Honda Air Blade giá tham khảo 200.000 đồng/ngày "
            "và 1.000.000 đồng/tuần.\n"
        )
        self.assertEqual(business_errors(article, {"business_claims": []}), [])

    def test_incorrect_wave_daily_price_is_still_rejected(self):
        article = "Giá thuê Honda Wave 200.000 đồng/ngày."
        self.assertIn(
            "Wrong rental rate:Honda Wave",
            business_errors(article, {"business_claims": []}),
        )


if __name__ == "__main__":
    unittest.main()
