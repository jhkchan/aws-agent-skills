"""Tests for eval/run_eval.py.

Covers:
  S-003 — discovery, skill loading, prompt building, Bedrock invocation (mocked).
  S-004 — assertion layer (must_contain / must_not_contain).
  S-005 — judge prompt, judge output parsing, grade bands, scorecard structure.
  S-E02 — missing verdict fields produce specific failure messages.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import (  # noqa: E402
    AssertionResult,
    build_scorecard,
    build_target_prompt,
    discover_eval_specs,
    grade_for_score,
    invoke_bedrock,
    load_judge_prompt,
    load_skill_definition,
    parse_judge_output,
    run_assertions,
    run_eval_for_skill,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# S-004 — Assertion layer validates skill output structure
# ---------------------------------------------------------------------------

GOOD_OUTPUT = """\
SECURITY_GROUP: bastion-ssh-open
VERDICT: OPEN
REASON: SSH port 22 is open to 0.0.0.0/0, exposing the instance to brute-force attacks.
REMEDIATION: Restrict to a bastion security group or use SSM Session Manager.
"""

TC_BASTION = {
    "id": "bastion-ssh-open",
    "expected_verdict": "OPEN",
    "assertions": {
        "must_contain": [
            "OPEN",
            "bastion-ssh-open",
            "VERDICT",
            "REASON",
            "REMEDIATION",
        ],
        "must_not_contain": ["Error:", "I cannot", "I'm unable", "VERDICT: RESTRICTED"],
    },
}


def test_must_contain_pass():
    """S-004: all must_contain tokens present -> assertion passes."""
    result = run_assertions(GOOD_OUTPUT, TC_BASTION)
    assert result.passed is True
    assert result.failures == []


def test_must_not_contain_pass():
    """S-004: no forbidden tokens present -> assertion passes."""
    result = run_assertions(GOOD_OUTPUT, TC_BASTION)
    assert result.passed is True


def test_must_not_contain_fail():
    """S-004: forbidden token present -> assertion fails."""
    bad_output = GOOD_OUTPUT + "Error: something went wrong\n"
    result = run_assertions(bad_output, TC_BASTION)
    assert result.passed is False
    assert any(
        f.check_type == "must_not_contain" and f.token == "Error:"
        for f in result.failures
    )


def test_must_contain_fail_missing_token():
    """S-004: a must_contain token missing -> assertion fails."""
    output_missing = "SECURITY_GROUP: bastion-ssh-open\nREASON: some reason\n"
    result = run_assertions(output_missing, TC_BASTION)
    assert result.passed is False
    assert any(
        f.check_type == "must_contain" and f.token == "VERDICT" for f in result.failures
    )


def test_assertion_result_has_test_case_id():
    """AssertionResult carries the test case id for traceability."""
    result = run_assertions(GOOD_OUTPUT, TC_BASTION)
    assert result.test_case_id == "bastion-ssh-open"


def test_run_assertions_multiple_cases_all_pass():
    """S-004: running assertions across 5 cases with correct verdicts -> 5/5 pass."""
    cases = [
        {
            "id": "bucket-safe-1",
            "assertions": {"must_contain": ["SAFE"], "must_not_contain": []},
        },
        {
            "id": "bucket-public-1",
            "assertions": {"must_contain": ["PUBLIC"], "must_not_contain": []},
        },
        {
            "id": "bucket-public-2",
            "assertions": {"must_contain": ["PUBLIC"], "must_not_contain": []},
        },
        {
            "id": "bucket-ambig-1",
            "assertions": {"must_contain": ["AMBIGUOUS"], "must_not_contain": []},
        },
        {
            "id": "bucket-safe-2",
            "assertions": {"must_contain": ["SAFE"], "must_not_contain": []},
        },
    ]
    outputs = [
        "VERDICT: SAFE",
        "VERDICT: PUBLIC",
        "VERDICT: PUBLIC",
        "VERDICT: AMBIGUOUS",
        "VERDICT: SAFE",
    ]
    for tc, out in zip(cases, outputs):
        result = run_assertions(out, tc)
        assert result.passed is True, f"Case {tc['id']} should pass"


# ---------------------------------------------------------------------------
# S-E02 — Missing verdict fields fail assertion with specific message
# ---------------------------------------------------------------------------

OUTPUT_MISSING_VERDICT = """\
SECURITY_GROUP: db-private-cidr
REASON: MySQL restricted to private CIDR.
REMEDIATION: None required.
"""

TC_DB = {
    "id": "db-private-cidr",
    "expected_verdict": "RESTRICTED",
    "assertions": {
        "must_contain": [
            "RESTRICTED",
            "db-private-cidr",
            "VERDICT",
            "REASON",
            "REMEDIATION",
        ],
        "must_not_contain": ["Error:", "VERDICT: OPEN"],
    },
}


def test_missing_verdict_fails_with_specific_message():
    """S-E02: missing VERDICT field produces a message naming the field and test case."""
    result = run_assertions(OUTPUT_MISSING_VERDICT, TC_DB)
    assert result.passed is False
    verdict_failures = [f for f in result.failures if f.token == "VERDICT"]
    assert len(verdict_failures) == 1
    msg = verdict_failures[0].message
    # Must name the missing field
    assert "VERDICT" in msg
    # Must name the test case / bucket
    assert "db-private-cidr" in msg
    # Must NOT be a generic "eval failed" message
    assert msg != "eval failed"


def test_missing_verdict_message_is_field_specific():
    """S-E02: the failure message identifies which check type failed."""
    result = run_assertions(OUTPUT_MISSING_VERDICT, TC_DB)
    assert result.passed is False
    f = result.failures[0]
    assert f.check_type == "must_contain"
    assert "not found" in f.message.lower()


def test_all_missing_fields_reported():
    """S-E02: multiple missing fields each get their own specific failure."""
    empty_output = "random text\n"
    result = run_assertions(empty_output, TC_DB)
    assert result.passed is False
    tokens_reported = {f.token for f in result.failures}
    assert "VERDICT" in tokens_reported
    assert "REASON" in tokens_reported
    assert "REMEDIATION" in tokens_reported
    assert "RESTRICTED" in tokens_reported
    assert "db-private-cidr" in tokens_reported


# ---------------------------------------------------------------------------
# S-005 — LLM-judge produces 8-dimension scorecard
# ---------------------------------------------------------------------------


def test_judge_prompt_file_exists():
    """S-005: judge_prompt.txt exists in eval/."""
    prompt_path = REPO_ROOT / "eval" / "judge_prompt.txt"
    assert prompt_path.exists()


def test_judge_prompt_has_8_dimensions():
    """S-005: the judge prompt defines exactly 8 dimensions (D1-D8)."""
    prompt = load_judge_prompt()
    for i in range(1, 9):
        assert f"D{i}" in prompt, f"Dimension D{i} missing from judge prompt"


def test_judge_prompt_has_max_15_per_dimension():
    """S-005: each dimension is scored out of 15 (8 x 15 = 120)."""
    prompt = load_judge_prompt()
    assert "15" in prompt
    assert "120" in prompt


def test_judge_prompt_requests_json_with_score_max_justification():
    """S-005: prompt instructs judge to output score, max, and justification per dimension."""
    prompt = load_judge_prompt()
    assert "score" in prompt.lower()
    assert "max" in prompt.lower()
    assert "justification" in prompt.lower()


def test_judge_prompt_requests_grade_and_total():
    """S-005: prompt instructs judge to output total score and grade band."""
    prompt = load_judge_prompt()
    assert "total" in prompt.lower()
    assert "grade" in prompt.lower()


def test_grade_bands():
    """S-005: grade band thresholds map correctly (120-point scale)."""
    assert grade_for_score(120) == "A"
    assert grade_for_score(108) == "A"
    assert grade_for_score(107) == "B"
    assert grade_for_score(84) == "B"
    assert grade_for_score(83) == "C"
    assert grade_for_score(60) == "C"
    assert grade_for_score(59) == "D"
    assert grade_for_score(36) == "D"
    assert grade_for_score(35) == "F"
    assert grade_for_score(0) == "F"


def test_build_scorecard_structure():
    """S-005: scorecard has all required fields (dimensions, total, grade, tokens, latency, model)."""
    dimensions = [
        {
            "id": f"D{i}",
            "name": f"Dim{i}",
            "score": 12,
            "max": 15,
            "justification": "ok",
        }
        for i in range(1, 9)
    ]
    card = build_scorecard(
        skill_name="test-skill",
        model_id="amazon.nova-pro-v1:0",
        dimensions=dimensions,
        token_count=500,
        latency_ms=1200,
        assertion_results=[AssertionResult(test_case_id="tc1", passed=True)],
    )
    assert card["skill"] == "test-skill"
    assert card["model_id"] == "amazon.nova-pro-v1:0"
    assert card["total_score"] == 96
    assert card["grade"] == "B"
    assert card["token_count"] == 500
    assert card["latency_ms"] == 1200
    assert len(card["dimensions"]) == 8
    assert card["assertions_passed"] is True
    assert card["assertions_passed_count"] == 1
    assert card["assertions_failed_count"] == 0


def test_build_scorecard_geo_blocked_zero():
    """S-E03 support: a 0-score scorecard is Grade F."""
    dimensions = [
        {
            "id": f"D{i}",
            "name": f"Dim{i}",
            "score": 0,
            "max": 15,
            "justification": "blocked",
        }
        for i in range(1, 9)
    ]
    card = build_scorecard(
        skill_name="test-skill",
        model_id="anthropic.claude-sonnet-5",
        dimensions=dimensions,
        token_count=0,
        latency_ms=0,
        assertion_results=[],
    )
    assert card["total_score"] == 0
    assert card["grade"] == "F"


# ---------------------------------------------------------------------------
# Eval spec discovery
# ---------------------------------------------------------------------------


def test_discover_eval_specs_finds_existing_skills():
    """S-003: runner discovers skills/*/eval/*.yaml by convention."""
    specs = discover_eval_specs(REPO_ROOT)
    assert len(specs) >= 3  # ec2 + iam + s3 seed skills
    skill_names = [s.parent.parent.name for s in specs]
    assert "ec2-security-group-auditor" in skill_names
    assert "iam-least-privilege-advisor" in skill_names
    assert "s3-public-access-auditor" in skill_names


def test_discover_eval_specs_returns_yaml_files():
    """Discovered specs are .yaml files inside eval/ dirs."""
    specs = discover_eval_specs(REPO_ROOT)
    for spec in specs:
        assert spec.suffix in (".yaml", ".yml")
        assert spec.parent.name == "eval"


# ---------------------------------------------------------------------------
# S-003 — Skill definition loading + prompt building + Bedrock invocation
# ---------------------------------------------------------------------------


def test_load_skill_definition_reads_existing():
    """S-003: load_skill_definition returns SKILL.md content."""
    content = load_skill_definition("ec2-security-group-auditor", REPO_ROOT)
    assert "EC2 Security-Group Auditor" in content
    assert "VERDICT" in content


def test_load_skill_definition_missing_raises():
    """S-003: missing SKILL.md raises FileNotFoundError."""
    import pytest

    with pytest.raises(FileNotFoundError):
        load_skill_definition("no-such-skill", REPO_ROOT)


def test_build_target_prompt_includes_skill_def():
    """S-003: prompt contains the skill definition."""
    prompt = build_target_prompt("# My Skill\nRules.", {"input": "data"})
    assert "# My Skill" in prompt
    assert "Rules." in prompt


def test_build_target_prompt_includes_test_case_input():
    """S-003: prompt contains the test case input verbatim."""
    prompt = build_target_prompt("skill", {"input": "Port: 22\nSource: 0.0.0.0/0"})
    assert "Port: 22" in prompt
    assert "0.0.0.0/0" in prompt


@patch("run_eval.subprocess.run")
def test_invoke_bedrock_returns_response_dict(mock_run):
    """S-003: invoke_bedrock calls aws bedrock-runtime converse and returns parsed dict."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "output": {"message": {"content": [{"text": "VERDICT: OPEN"}]}},
                "usage": {"totalTokens": 150, "inputTokens": 100, "outputTokens": 50},
            }
        ),
        stderr="",
    )
    response = invoke_bedrock("amazon.nova-pro-v1:0", "test prompt")
    assert response["output"]["message"]["content"][0]["text"] == "VERDICT: OPEN"
    assert response["usage"]["totalTokens"] == 150


@patch("run_eval.subprocess.run")
def test_invoke_bedrock_cli_uses_locked_profile_and_region(mock_run):
    """S-003: CLI uses locked defaults —profile default —region us-east-1."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "output": {"message": {"content": [{"text": "ok"}]}},
                "usage": {"totalTokens": 10},
            }
        ),
        stderr="",
    )
    invoke_bedrock("amazon.nova-pro-v1:0", "p")
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "aws"
    assert "bedrock-runtime" in cmd
    assert "converse" in cmd
    assert "--profile" in cmd
    assert "default" in cmd
    assert "--region" in cmd
    assert "us-east-1" in cmd


@patch("run_eval.subprocess.run")
def test_invoke_bedrock_passes_locked_model_id_and_temperature(mock_run):
    """S-003: CLI payload contains amazon.nova-pro-v1:0 and temperature 0.0."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "output": {"message": {"content": [{"text": "ok"}]}},
                "usage": {"totalTokens": 5},
            }
        ),
        stderr="",
    )
    invoke_bedrock("amazon.nova-pro-v1:0", "p", temperature=0.0)
    cmd = mock_run.call_args[0][0]
    payload = json.loads(cmd[cmd.index("--cli-input-json") + 1])
    assert payload["modelId"] == "amazon.nova-pro-v1:0"
    assert payload["inferenceConfig"]["temperature"] == 0.0


@patch("run_eval.subprocess.run")
def test_invoke_bedrock_propagates_unexpected_called_process_error(mock_run):
    """S-003: unexpected CalledProcessError from subprocess propagates (caller handles)."""
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=255,
        cmd=["aws"],
        stderr="ExpiredTokenException",
    )
    import pytest

    with pytest.raises(subprocess.CalledProcessError):
        invoke_bedrock("amazon.nova-pro-v1:0", "p")


# ---------------------------------------------------------------------------
# S-005 — Judge output parsing robustness
# ---------------------------------------------------------------------------


def _judge_dims(score=12):
    return [
        {
            "id": f"D{i}",
            "name": f"Dim{i}",
            "score": score,
            "max": 15,
            "justification": "ok",
        }
        for i in range(1, 9)
    ]


def test_parse_judge_output_clean_json():
    """S-005: parse clean JSON with all 8 dimensions."""
    text = json.dumps({"dimensions": _judge_dims(13), "total": 104})
    dims = parse_judge_output(text)
    assert len(dims) == 8
    assert dims[0]["id"] == "D1"
    assert dims[0]["score"] == 13


def test_parse_judge_output_code_block():
    """S-005: parse JSON wrapped in markdown code fences."""
    text = "```json\n" + json.dumps({"dimensions": _judge_dims(10)}) + "\n```"
    dims = parse_judge_output(text)
    assert len(dims) == 8
    assert all(d["score"] == 10 for d in dims)


def test_parse_judge_output_malformed_returns_zeros():
    """S-005: malformed judge output falls back to 8 zero-score dimensions."""
    dims = parse_judge_output("this is not JSON")
    assert len(dims) == 8
    assert all(d["score"] == 0 for d in dims)


def test_parse_judge_output_clamps_oversized_scores():
    """S-005: scores above max are clamped to 15."""
    text = json.dumps(
        {"dimensions": [{"id": f"D{i}", "score": 999} for i in range(1, 9)]}
    )
    dims = parse_judge_output(text)
    for d in dims:
        assert d["score"] <= 15


def test_parse_judge_output_fills_missing_dimensions():
    """S-005: missing dimensions are filled with score 0."""
    text = json.dumps({"dimensions": [{"id": "D1", "score": 10}]})
    dims = parse_judge_output(text)
    assert len(dims) == 8
    d1 = next(d for d in dims if d["id"] == "D1")
    assert d1["score"] == 10
    d2 = next(d for d in dims if d["id"] == "D2")
    assert d2["score"] == 0


def test_parse_judge_output_includes_max_and_justification():
    """S-005: each dimension has max and justification fields."""
    text = json.dumps({"dimensions": _judge_dims(12)})
    dims = parse_judge_output(text)
    for d in dims:
        assert "max" in d
        assert "justification" in d


# ---------------------------------------------------------------------------
# S-003 / S-004 / S-005 — Full pipeline with mocked Bedrock
# ---------------------------------------------------------------------------


@patch("run_eval.invoke_bedrock")
def test_run_eval_for_skill_mocked_pipeline(mock_invoke):
    """S-003/S-005: full pipeline discovers spec, invokes model+judge, emits scorecard."""
    specs = discover_eval_specs(REPO_ROOT)
    ec2_spec = next(s for s in specs if "ec2" in s.parent.parent.name)

    judge_json = json.dumps({"dimensions": _judge_dims(12), "total": 96})

    def mock_fn(model_id, prompt, *args, **kwargs):
        if "rubric" in prompt.lower() or "evaluator" in prompt.lower():
            # Judge call uses a different model family (less peer-leniency
            # than Nova-judging-Nova).
            assert model_id == "openai.gpt-oss-120b-1:0"
            return {
                "output": {"message": {"content": [{"text": judge_json}]}},
                "usage": {"totalTokens": 200},
            }
        # Target (skill-execution) call uses Nova Pro.
        assert model_id == "amazon.nova-pro-v1:0"
        return {
            "output": {
                "message": {
                    "content": [{"text": "VERDICT: OPEN\nREASON: x\nREMEDIATION: y"}]
                }
            },
            "usage": {"totalTokens": 100},
        }

    mock_invoke.side_effect = mock_fn
    sc = run_eval_for_skill(ec2_spec)

    assert sc is not None
    assert sc["skill"] == "ec2-security-group-auditor"
    assert sc["model_id"] == "amazon.nova-pro-v1:0"
    assert sc["max_score"] == 120
    assert len(sc["dimensions"]) == 8
    assert sc["total_score"] == 96
    assert sc["token_count"] == 600  # 3 judge runs (median-of-3) x 200 tokens
    assert mock_invoke.call_count >= 8  # 5 test cases + 3 judge runs (median-of-3)


def test_run_eval_for_skill_assertion_only():
    """S-003: assertion-only mode skips model invocation, emits lightweight scorecard."""
    specs = discover_eval_specs(REPO_ROOT)
    ec2_spec = next(s for s in specs if "ec2" in s.parent.parent.name)
    sc = run_eval_for_skill(ec2_spec, assertion_only=True)
    assert sc is not None
    assert sc["total_score"] == 0
    assert sc["token_count"] == 0
    assert sc["dimensions"] == []
