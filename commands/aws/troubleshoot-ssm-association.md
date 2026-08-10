---
description: Diagnose AWS Systems Manager (SSM) association failures via a 5-symptom decision tree and 3-layer health check.
nl_triggers:
  - "SSM association failed"
  - "association TimedOut"
  - "association never runs"
  - "association not running"
  - "instance not in SSM"
  - "instance not managed"
  - "SSM agent unreachable"
  - "SSM ConnectionLost"
  - "association execution failed"
  - "document execution fails"
  - "patch association failed"
  - "inventory association failed"
  - "association wrong schedule"
  - "association targets wrong"
  - "association enabled false"
  - "SSM rate limiting"
  - "IAM role missing SSM"
  - "AmazonSSMManagedInstanceCore"
  - "hybrid activation expired"
  - "SSM VPC endpoints missing"
routes_to: ssm-association-troubleshooter
---

# /aws:troubleshoot-ssm-association

Activate the `ssm-association-troubleshooter` skill and diagnose
an SSM association failure via a systematic 5-symptom decision
tree and 3-layer health check (IAM, connectivity, agent).

## What it does

Reads an association-id (or association name + instance-id) and
observed symptom, then applies a 6-step diagnostic process:

1. Run the 3-layer SSM health check (IAM, connectivity, agent).
2. Diagnose association status: Failed (invalid parameters,
   document not found, S3 access denied).
3. Diagnose association status: TimedOut (agent unreachable,
   instance offline, network connectivity).
4. Diagnose instance not appearing in SSM (not managed): missing
   IAM role, missing VPC endpoints, agent not running, hybrid
   activation expired.
5. Diagnose association never runs: wrong cron expression, tag
   mismatch, association Disabled, rate limiting.
6. Diagnose document execution fails mid-run: script error,
   permission denied, platform unsupported, version drift.

Emits a deterministic VERDICT per diagnosis:

```text
DIAGNOSIS: <reference>
ASSOCIATION: <association-id>
INSTANCE: <instance-id>
SYMPTOM: Failed | TimedOut | NotManaged | NeverRuns | DocumentError
ROOT_CAUSE: <specific cause cited>
EVIDENCE: <diagnostic signals>
LAYER_CHECK: IAM / Connectivity / Agent
FIX: <action with CLI snippet>
VERIFICATION: <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

## When to invoke

Paste an association-id and symptom, or live diagnostic output,
and ask any of:

- "why is my SSM association failing"
- "why did the patch association time out"
- "why is this instance not showing in SSM"
- "why is my association not running on schedule"
- "the document script is erroring mid-run"
- "instance is ConnectionLost, can't reach SSM"
- "hybrid mi-* instance disappeared from SSM"
- "association targets don't match"

A bare "association-id + symptom" also routes here via the
orchestrator.

## Inputs

- Association-id or association name.
- Instance-id (or `mi-*` for hybrid).
- Observed symptom (Failed / TimedOut / never-runs / document-error
  / instance-missing).
- Region.
- Execution-id (optional, for per-target drill-down).
- Recent CLI output from `describe-instance-information`,
  `describe-association-executions`, etc. (optional, speeds
  diagnosis).
- SSM agent log excerpt (optional, for document-level errors).

## Outputs

- One DIAGNOSIS block per association with SYMPTOM, ROOT_CAUSE,
  EVIDENCE, LAYER_CHECK, FIX, VERIFICATION, VERDICT, NEXT_STEP,
  and ESCALATION_PATH fields.
- For ROOT_CAUSE_FOUND: a specific cause + actionable fix CLI.
- For NEED_MORE_INFO: the specific next diagnostic to run (with
  the exact command).
- For ESCALATE: the escalation path (AWS Support, on-prem
  operator, etc.) with the information to include.
- The 3-layer SSM health check result for every diagnosis.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 2 Troubleshoot specialist for Management/SSM).
- `/aws:audit-ssm-managed-instance` for fleet-wide SSM posture
  audit (companion to this skill's per-association focus).
- `/aws:deploy-ssm-association` for association deployment (the
  Deploy companion to this Troubleshoot skill).
