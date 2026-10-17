"""Tests for production live GitHub security readback. No network."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from production_security import check_security, ruleset_protects_privileged_code, privileged_codeowners_present, PRIVILEGED_PATTERNS


def rule(review=True, count=1, bypass=None):
    return {"id": 25248247, "enforcement": "active",
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "bypass_actors": [] if bypass is None else bypass,
            "rules": [{"type": "deletion"}, {"type": "non_fast_forward"},
                      {"type": "pull_request", "parameters":
                       {"required_approving_review_count": count,
                        "require_code_owner_review": review}}]}


class SecurityPreflightTests(unittest.TestCase):
    def test_current_ruleset_is_insufficient(self):
        r = rule()
        r["rules"] = r["rules"][:2]
        self.assertFalse(ruleset_protects_privileged_code(r))

    def test_codeowners_required(self):
        self.assertFalse(ruleset_protects_privileged_code(rule(review=False)))
        # With CODEOWNER review enabled, zero *generic* approvals does not
        # remove the mandatory owner review for privileged files.
        self.assertTrue(ruleset_protects_privileged_code(rule(count=0)))
        self.assertFalse(ruleset_protects_privileged_code(rule(count=-1)))
        self.assertFalse(ruleset_protects_privileged_code(rule(bypass=[{"actor_id": 1}])))

    def test_local_codeowners_covers_all_privileged_sources(self):
        from pathlib import Path
        content=(Path(__file__).resolve().parents[1]/'.github/CODEOWNERS').read_text()
        self.assertTrue(privileged_codeowners_present(content))
        for pattern in PRIVILEGED_PATTERNS:
            self.assertFalse(privileged_codeowners_present(
                content.replace(pattern + ' @thuexemayhanoi', '')))

    def test_empty_or_fake_owner_is_not_accepted(self):
        self.assertFalse(privileged_codeowners_present(''))
        self.assertFalse(privileged_codeowners_present('/.github/ @attacker'))
        self.assertFalse(privileged_codeowners_present('/.github/ @thuexemayhanoi\\n'
                                                     '/scripts/ @attacker'))

    def test_only_main_protection_is_valid(self):
        r = rule()
        r["conditions"]["ref_name"]["include"] = ["refs/heads/develop"]
        self.assertFalse(ruleset_protects_privileged_code(r))

    def test_strict_protection_can_pass(self):
        self.assertTrue(ruleset_protects_privileged_code(rule()))

    def test_live_readback_failure_blocks(self):
        self.assertEqual(check_security(lambda url,token: (_ for _ in ()).throw(OSError("unavailable")), "")["status"],"BLOCKED")

    def test_live_readback_enforced(self):
        def fetch(url,token):
            if url.endswith("/branches/main"):
                return {"protected": True}
            if url.endswith("/rulesets"):
                return [{"id": 25248247,"enforcement":"active"}]
            return rule()
        self.assertEqual(check_security(fetch,"")["status"],"PASS")

    def test_old_main_protection_blocks(self):
        def fetch(url,token):
            if url.endswith("/branches/main"):
                return {"protected": True}
            if url.endswith("/rulesets"):
                return [{"id": 25248247,"enforcement":"active"}]
            x=rule(); x["rules"]=x["rules"][:2]; return x
        self.assertEqual(check_security(fetch,"")["status"],"BLOCKED")


if __name__ == "__main__":
    unittest.main()
