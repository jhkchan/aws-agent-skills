"""Tests for eval/run_eval.py — T-8 verification scenarios S-E01, S-E03, S-N01.

Written FIRST per TDD discipline; implementation must make these pass.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# S-E01 — SSO expiration handled gracefully
# ---------------------------------------------------------------------------

class TestSSOExpirationSE01:
    """S-E01: SSO session expired → clear message, exit(1), no partial artifacts."""

    def test_sso_error_raises_with_login_command(self):
        """invoke_bedrock raises SSOSessionExpiredError containing the login hint."""
        from eval.run_eval import SSOSessionExpiredError, invoke_bedrock

        with patch("eval.run_eval.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=254,
                stdout="",
                stderr="ExpiredTokenException: The SSO session "
                "associated with this profile has expired.",
            )
            with pytest.raises(SSOSessionExpiredError) as exc:
                invoke_bedrock("amazon.nova-pro-v1:0", "prompt")
            assert "aws sso login --profile default" in str(exc.value)

    def test_sso_expired_exits_without_scorecard(self, tmp_path):
        """run_eval_for_spec exits(1) and writes zero scorecard files."""
        from eval.run_eval import run_eval_for_spec

        scorecards_dir = tmp_path / "scorecards"
        scorecards_dir.mkdir()
        spec = {
            "skill": "test-skill",
            "model_id": "amazon.nova-pro-v1:0",
            "profile": "default",
            "region": "us-east-1",
            "temperature": 0.0,
            "test_cases": [
                {
                    "id": "t1",
                    "input": "test",
                    "expected_verdict": "OK",
                    "assertions": {"must_contain": [], "must_not_contain": []},
                }
            ],
        }
        with patch("eval.run_eval.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=254,
                stdout="",
                stderr="ExpiredTokenException: SSO session expired",
            )
            with pytest.raises(SystemExit) as exc:
                run_eval_for_spec(spec, "# Skill", str(scorecards_dir))
            assert exc.value.code == 1

        assert list(scorecards_dir.glob("*.json")) == []


# ---------------------------------------------------------------------------
# S-E03 — Claude geo-block produces documented 0/120
# ---------------------------------------------------------------------------

class TestGeoBlockSE03:
    """S-E03: anthropic.* + ValidationException → 0/120 Grade F scorecard."""

    def test_geoblock_scorecard_is_zero_over_120_grade_f(self):
        from eval.run_eval import make_geoblock_scorecard

        sc = make_geoblock_scorecard("test-skill", "anthropic.claude-sonnet-5")
        assert sc["total_score"] == 0
        assert sc["max_score"] == 120
        assert sc["grade"] == "F"

    def test_geoblock_justification_distinguishes_account_vs_region(self):
        from eval.run_eval import make_geoblock_scorecard

        sc = make_geoblock_scorecard("test-skill", "anthropic.claude-sonnet-5")
        j = sc["justification"]
        assert "ValidationException" in j
        assert "account-level" in j
        assert "region-level" in j

    def test_geoblock_produces_and_writes_scorecard(self, tmp_path):
        from eval.run_eval import run_eval_for_spec

        scorecards_dir = tmp_path / "scorecards"
        scorecards_dir.mkdir()
        spec = {
            "skill": "test-skill",
            "model_id": "anthropic.claude-sonnet-5",
            "profile": "default",
            "region": "us-east-1",
            "temperature": 0.0,
            "test_cases": [
                {
                    "id": "t1",
                    "input": "test",
                    "expected_verdict": "OK",
                    "assertions": {"must_contain": [], "must_not_contain": []},
                }
            ],
        }
        with patch("eval.run_eval.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=254,
                stdout="",
                stderr='{"type":"ValidationException"}: '
                "Invocation failed — model not available",
            )
            sc = run_eval_for_spec(spec, "# Skill", str(scorecards_dir))

        assert sc["total_score"] == 0
        assert sc["grade"] == "F"
        assert sc.get("geo_blocked") is True
        files = list(scorecards_dir.glob("*.json"))
        assert len(files) == 1


# ---------------------------------------------------------------------------
# S-N01 — Cost-zero compliance verified
# ---------------------------------------------------------------------------

class TestCostZeroSN01:
    """S-N01: only stateless bedrock-runtime converse calls, no persistent
    resources."""

    FORBIDDEN_SUBSTRINGS = [
        "create-role",
        "create-bucket",
        "create-function",
        "create-stack",
        "put-bucket",
        "deploy",
        "register-task",
        "allocate-address",
        "run-instances",
        "provision",
    ]

    def _mock_success_response(self):
        return MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "output": {
                        "message": {
                            "content": [
                                {"text": "VERDICT: OK\nREASON: test\nREMEDIATION: none"}
                            ]
                        }
                    },
                    "usage": {"totalTokens": 10},
                }
            ),
            stderr="",
        )

    def test_full_run_only_uses_converse(self, tmp_path):
        from eval.run_eval import run_eval_for_spec

        scorecards_dir = tmp_path / "scorecards"
        scorecards_dir.mkdir()
        spec = {
            "skill": "test-skill",
            "model_id": "amazon.nova-pro-v1:0",
            "profile": "default",
            "region": "us-east-1",
            "temperature": 0.0,
            "test_cases": [
                {
                    "id": "t1",
                    "input": "test",
                    "expected_verdict": "OK",
                    "assertions": {
                        "must_contain": ["VERDICT"],
                        "must_not_contain": ["Error:"],
                    },
                }
            ],
        }
        with patch("eval.run_eval.subprocess.run") as mock_run:
            mock_run.return_value = self._mock_success_response()
            run_eval_for_spec(spec, "# Skill", str(scorecards_dir))

        assert mock_run.call_count > 0, "Expected at least one Bedrock call"
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            cmd_str = " ".join(cmd)
            assert "converse" in cmd_str, f"Non-converse call: {cmd_str}"
            for bad in self.FORBIDDEN_SUBSTRINGS:
                assert bad not in cmd_str.lower(), (
                    f"Cost-zero violation: '{bad}' in {cmd_str}"
                )
