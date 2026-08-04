---
description: Audit a Cost and Usage Report (CUR) configuration for coverage, staleness, version, Athena integration, S3 versioning, and time-horizon health.
nl_triggers:
  - "audit this Cost and Usage Report"
  - "check CUR configuration"
  - "is my CUR healthy"
  - "CUR Athena integration"
  - "why is my CUR stale"
  - "CUR report version"
  - "is hourly refresh enabled"
  - "CUR S3 bucket versioning"
  - "CUR not delivering"
  - "FinOps data pipeline audit"
  - "Athena cost query empty"
  - "CUR manifest check"
  - "cost and usage report"
  - "billing report audit"
routes_to: cur-cost-usage-report-auditor
---

# /aws:audit-cur-cost-usage-report

Activate the `cur-cost-usage-report-auditor` skill and audit one or more
CUR report definitions for FinOps data pipeline health.

## What it does

Reads a CUR report definition (from `aws cur describe-report-definitions`)
plus S3 bucket metadata (versioning, latest manifest timestamp) and applies
the ordered classification logic:

1. Pre-flight account context gate — short-circuit linked accounts (CUR is
   payer-only) and non-us-east-1 API regions.
2. NO_CUR — zero report definitions on the payer account.
3. STALE — hourly manifest > 48h old or daily manifest > 72h old.
4. CONFIG_GAP — report version, format, Athena integration, S3 versioning,
   Resources schema element, RefreshClosedReports (Steps 3a-3f).
5. OK — all dimensions pass.

Emits a deterministic VERDICT per report definition:

```text
REPORT: <report-name>
VERDICT: NO_CUR | STALE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the specific finding and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step Na)>
  - [HIGH] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CUR report definition and S3 metadata and ask any of:

- "audit this Cost and Usage Report"
- "is my CUR healthy?"
- "why are my Athena cost queries empty?"
- "is CUR delivering to S3?"
- "check CUR Athena integration"
- "is hourly refresh enabled?"

A bare CUR report name + any audit verb also routes here.

## Inputs

- A CUR report definition JSON (from `aws cur describe-report-definitions`),
  pasted inline or referenced by file path.
- S3 metadata: latest manifest timestamp, bucket versioning status.
- For live-account audits: just the payer account id + region.

## Outputs

- One VERDICT block per report definition (multiple findings aggregate
  to the worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: create CUR, update format, add Athena artifact,
  enable versioning, add Resources schema, enable RefreshClosedReports.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for FinOps cost visibility).
- `/aws:audit-compute-optimizer-findings` for EC2/EBS/Lambda right-sizing
  recommendations that depend on CUR data.
