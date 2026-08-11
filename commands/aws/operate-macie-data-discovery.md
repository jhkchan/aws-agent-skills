---
description: Manage Amazon Macie data discovery operations — enable Macie (org-level delegated admin), create classification jobs, configure managed and custom data identifiers, manage findings and suppression rules, enable automated ML-based discovery, integrate with Security Hub, wire Lambda/Step Functions for auto-remediation.
nl_triggers:
  - "enable macie"
  - "macie delegated admin"
  - "macie classification job"
  - "create macie job"
  - "macie custom data identifier"
  - "macie findings"
  - "macie security hub"
  - "macie automated discovery"
  - "macie remediation lambda"
  - "macie suppression rules"
  - "macie sensitive data"
  - "macie s3 scanning"
  - "macie pii detection"
  - "macie step functions"
  - "macie eventbridge"
  - "macie auto-remediation"
  - "macie cross-account"
  - "macie org level"
routes_to: macie-data-discovery-operator
---

# /aws:operate-macie-data-discovery

Activate the `macie-data-discovery-operator` skill and plan/execute a
Macie data discovery operation with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a Macie operation request and applies the pre-check sequence:

1. Pre-flight Macie enablement + delegated admin gate — short-circuit
   cases where Macie is not enabled or delegated admin is not set.
2. Pre-check gate — BLOCKED if any check fails (Macie disabled, buckets
   missing, IAM permissions insufficient, SH not enabled).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected finding behavior, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot state, execute the CLI, wait
   for job/finding state transition.
5. Post-verification — describe resources match expected config, job
   status correct, findings published. COMPLETED only if ALL post-
   verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <enable | classify | custom-id | findings | suppress | auto-discovery | security-hub | remediate | aggregate>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <macie-resource-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
POST_VERIFY:
  - [PASS] <verification description>
STATE: <job status / finding state / Macie status>
NOTES: <detection coverage, severity, remediation caveats>
```

## When to invoke

Paste a Macie operation request, or describe the scenario:

- "enable Macie for our organization"
- "create a daily classification job on prod-data-bucket"
- "create a custom data identifier for employee IDs"
- "set up Macie auto-remediation via Step Functions"
- "forward Macie findings to Security Hub"
- "suppress findings on test-environment buckets"
- "enable automated ML-based discovery"

## Inputs

- Target operation (enable, classify, custom-id, findings, suppress,
  auto-discovery, security-hub, remediate, aggregate).
- For classify: bucket names, schedule (one-time / daily / weekly /
  monthly), managed identifier selector (ALL / RECOMMENDED / specific).
- For custom-id: regex pattern, proximity keywords, ignore words,
  maximum match distance, severity.
- For remediate: EventBridge rule, Lambda or Step Functions ARN,
  finding severity scope.
- Account ID, region.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected finding behavior, and the
  CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the resource
  state, and any follow-up recommendations.
- For BLOCKED: the specific failure reason and remediation step.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for Macie data discovery).
- `/aws:audit-securityhub-finding` for Security Hub finding triage.
- `/aws:audit-guardduty-finding` for GuardDuty threat detection.
