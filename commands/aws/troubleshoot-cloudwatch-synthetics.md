---
name: troubleshoot-cloudwatch-synthetics
description: >-
  Slash command for the cloudwatch-synthetics-troubleshooter skill.
  Diagnoses CloudWatch Synthetics canary failures via a symptom-to-cause
  decision tree covering all five canary types (GUI Selenium, HTTP, API,
  broken-link, multi-step), runtime exceptions, Visual Monitoring
  baseline mismatches, authentication failures, timeouts, and blue/green
  deployment artifact issues. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO |
  ESCALATE with the specific failure type and evidence.
skill: cloudwatch-synthetics-troubleshooter
family: Management
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-cloudwatch-synthetics

Invoke the `cloudwatch-synthetics-troubleshooter` skill to diagnose a
CloudWatch Synthetics canary failure.

Read the skill at `skills/cloudwatch-synthetics-troubleshooter/SKILL.md`
and follow its diagnostic procedure to identify the root cause.

## When to use

- A Synthetics canary has transitioned to FAILED state.
- CloudWatch `SuccessPercent` for a canary is below threshold.
- Visual Monitoring reports a `VisualMonitoringBaselineMismatch`.
- Canary runs are timing out (Duration at `TimeoutInSeconds`).
- The canary cannot authenticate (401/403, "Login failed").
- Run report shows runtime exceptions (`TypeError`, `NoSuchElementException`).
- Broken-link checker is failing.
- Multiple canaries failed simultaneously (shared execution role issue).
- Canary cannot access its artifact bucket (`AccessDenied`, `NoSuchBucket`).

## Invocation

```
/aws:troubleshoot-cloudwatch-synthetics <canary name / symptom description>
```

The skill will:

1. Identify the symptom category (TIMEOUT, AUTH_FAILURE,
   VISUAL_MONITORING_MISMATCH, RUNTIME_EXCEPTION, TARGET_ENDPOINT_DOWN,
   ARTIFACT_MISMATCH, INSUFFICIENT_PERMISSIONS, RATE_LIMITED,
   NETWORK_ERROR, DNS_FAILURE).
2. Request the canary name and run report error string.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with CloudWatch `SuccessPercent`, `Duration`, canary
   logs, Secrets Manager rotation state, IAM permissions, and artifact
   bucket access as required by the category.
5. Map to the root-cause catalog (11 patterns covering the majority of
   canary failure incidents).
6. Verify the proposed fix before recommending.
7. Emit the standard VERDICT block.

## Output shape

```text
CANARY: <canary name> in <region>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <failure type> — <specific root cause>
FAILURE_TYPE: <TIMEOUT | AUTH_FAILURE | VISUAL_MONITORING_MISMATCH | ...>
EVIDENCE:
  - <run report signal>: <value>
  - <CloudWatch metric signal>: <value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific fix + verification command>
```

## Pre-flight

The skill requires the canary name and region. Ideally the operator
also provides the run report error string (from `get-canary-runs`), the
canary type (GUI Selenium, HTTP, API, broken-link, multi-step), the
CloudWatch `SuccessPercent` pattern, and whether a recent deployment
occurred. If the canary name is unknown, the skill will suggest
`aws synthetics describe-canaries --query 'Canaries[?State==`ERROR`]'`
to surface failing canaries. If the user provides only a vague symptom
with no identifying info, the skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/cloudwatch-synthetics-troubleshooter/SKILL.md`
- Reference: `skills/cloudwatch-synthetics-troubleshooter/references/canary-type-reference.md`
- Reference: `skills/cloudwatch-synthetics-troubleshooter/references/visual-monitoring-guide.md`
- AWS docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html
