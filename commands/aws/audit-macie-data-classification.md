---
description: Audit Amazon Macie data-classification posture — classification job coverage, ASDD enablement, sensitive data finding triage (PII/credentials/financial), allow-list scope, and Security Hub export integration.
nl_triggers:
  - "audit macie classification"
  - "check macie findings"
  - "are there untriaged macie findings"
  - "is sensitive data discovery enabled"
  - "macie allow list too broad"
  - "macie security hub export"
  - "macie classification job failed"
  - "sensitive data in s3"
  - "pii audit macie"
  - "macie posture check"
  - "macie automated discovery"
  - "macie custom data identifiers"
  - "macie allow list scope"
  - "macie findings triage"
  - "data classification audit"
  - "dlp audit s3"
routes_to: macie-data-classification-auditor
---

# /aws:audit-macie-data-classification

Activate the `macie-data-classification-auditor` skill and audit an
Amazon Macie data-classification posture for coverage, triage, and
configuration gaps.

## What it does

Reads a Macie posture snapshot (session status, ASDD config,
classification jobs, findings, allow list, Security Hub integration) and
applies the ordered classification logic:

1. Coverage gate — no active jobs AND ASDD disabled means
   NO_CLASSIFICATION (zero sensitive-data visibility).
2. Findings triage — open (non-archived) HIGH-severity findings trigger
   UNTRIAGED_FINDINGS (credentials, SSN, credit card).
3. Configuration gap — Security Hub export disabled, wildcard allow-list
   prefixes, auto-archive filters, or stale ASDD trigger CONFIG_GAP.
4. OK — all dimensions pass.

Emits a deterministic VERDICT per account scope:

```text
ACCOUNT: <account-id> (<region>)
VERDICT: NO_CLASSIFICATION | UNTRIAGED_FINDINGS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - [NO_CLASSIFICATION] <description (Step Na)>
  - [CONFIG_GAP] <description (Step Nb)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

## When to invoke

Paste a Macie posture snapshot and ask any of:

- "audit our macie classification coverage"
- "check for untriaged macie findings"
- "is sensitive data discovery enabled?"
- "is our macie allow list too broad?"
- "does macie export to security hub?"
- "why did our macie classification job fail?"

A bare account ID + any audit verb ("audit macie", "check macie posture")
also routes here via the orchestrator.

## Inputs

- A Macie posture snapshot including: session status (ENABLED / PAUSED /
  DISABLED), ASDD configuration (status, lastRunTime), classification
  jobs (jobStatus, samplingPercentage, buckets), findings (severity,
  archived, type, classificationDetails), allow lists (criteria, scope),
  and Security Hub export status.
- For live-account audits: an account ID and region — the skill emits
  the AWS CLI commands to retrieve the full posture.

## Outputs

- One VERDICT block per account scope (first matching step determines
  the verdict).
- Enumerated FINDINGS list with step citations.
- Specific remediation: enable ASDD, create classification jobs, rotate
  exposed credentials, archive findings after investigation, enable
  Security Hub export, scope allow-list entries — all with CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for data security and compliance).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  compliance — Macie findings flow into Security Hub as findings, which
  this companion skill triages.
