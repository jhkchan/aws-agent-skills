---
description: Audit a DLM (Data Lifecycle Manager) EBS snapshot lifecycle policy for coverage gaps, disabled state, empty tag/resource targets, invalid schedules, weak retention, missing cross-region copy (DR gap), CopyTags metadata loss, and per-volume snapshot quota risk.
nl_triggers:
  - "audit this DLM lifecycle policy"
  - "check DLM EBS snapshots"
  - "is my DLM policy enabled"
  - "why did my EBS snapshots stop"
  - "DLM silent failure"
  - "EBS backup coverage"
  - "lifecycle policy disabled"
  - "DLM cross-region copy"
  - "check DLM retention"
  - "is DLM working"
  - "audit EBS backup posture"
  - "DLM policy misconfigured"
  - "snapshot policy gap"
  - "Data Lifecycle Manager audit"
routes_to: dlm-lifecycle-policy-auditor
---

# /aws:audit-dlm-lifecycle-policy

Activate the `dlm-lifecycle-policy-auditor` skill and audit one or more DLM
EBS snapshot lifecycle policies (or an account's overall DLM coverage) for
backup posture and silent-failure modes.

## What it does

Reads a DLM lifecycle policy document (from `get-lifecycle-policy`) plus
optional account context (volume list, all-policies list) and applies the
ordered classification logic:

1. Workload coverage — does ANY enabled DLM policy protect these volumes?
   Zero enabled policies targeting the workload's tags is NO_POLICY.
2. State check — DISABLED policy creates zero snapshots (MISCONFIGURED).
3. Target coverage — empty TargetTags / ResourceTypes match zero volumes
   (MISCONFIGURED).
4. Schedule validity — missing/invalid CreateRule, 5-field cron
   (MISCONFIGURED). DLM requires 6-field cron (with year).
5. Retention validity — missing RetainRule entirely = unbounded retention
   that silently hits the per-volume 1,000-snapshot quota (MISCONFIGURED).
6. Retention strength — Count:1 or <7-day interval = no recovery history
   (CONFIG_GAP).
7. DR coverage — no CrossRegionCopyTargets = single-region backup
   (CONFIG_GAP).
8. Metadata preservation — CopyTags false/absent drops source volume tags
   (CONFIG_GAP).
9. Quota/cost risk — Count >= 1000 (quota cliff) or FastRestoreRule on
   non-boot volumes (CONFIG_GAP).
10. Aggregation — worst finding wins (NO_POLICY > MISCONFIGURED > CONFIG_GAP > OK).

Emits a deterministic VERDICT per policy:

```text
POLICY: <policy-id or "ACCOUNT/<workload>">
VERDICT: NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [MISCONFIGURED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a DLM lifecycle policy JSON (from `get-lifecycle-policy`) and ask any
of:

- "audit this DLM lifecycle policy"
- "why did my EBS snapshots stop?"
- "is my backup policy enabled?"
- "check DLM retention and DR"
- "is DLM actually working?"
- "does this account have EBS backup coverage?"

A bare policy id + any audit verb ("audit this lifecycle policy", "check DLM
coverage") also routes here via the orchestrator.

## Inputs

- A DLM lifecycle policy document (JSON, from `get-lifecycle-policy`),
  pasted inline or referenced by file path.
- For account-coverage audits: the list of all DLM policies
  (`get-lifecycle-policies` output) and the workload's volume tag set.
- Optional execution-verification signal: the output of
  `aws ec2 describe-snapshots --filters "Name=tag:aws:dlm:lifecycle-policy-id,Values=<id>"`
  — the ground-truth check that the policy has actually produced snapshots.

## Outputs

- One VERDICT block per policy (multiple findings aggregate to the worst
  verdict).
- For account-coverage audits: one VERDICT block per workload, where
  NO_POLICY means no enabled policy targets the workload's volume tags.
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: re-enable disabled policies, add TargetTags, fix
  cron syntax, add CrossRegionCopyTargets, enable CopyTags, tune retention.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Storage / DLM EBS backup resilience).
- `/aws:audit-kms-key-policy` when DLM cross-region copy uses a customer-
  managed KMS key in the DR region — audit that key's policy for cross-
  account exposure.
