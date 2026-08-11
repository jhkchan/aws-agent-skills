---
description: Design and emit a CUR (Cost and Usage Report) automation stack — CUR definition, Athena integration with partition projection, FinOps query automation, QuickSight dashboards, Cost Categories, cost allocation tag activation, CUR 2.0 split cost allocation, BCM Data Exports, Amazon Q cost analysis.
nl_triggers:
  - "set up CUR"
  - "create Cost and Usage Report"
  - "CUR Athena integration"
  - "CUR partition projection"
  - "Athena CUR table"
  - "top spenders query"
  - "unused resources FinOps"
  - "Savings Plan opportunities"
  - "Reserved Instance utilization"
  - "tag compliance CUR"
  - "QuickSight cost dashboard"
  - "SPICE dataset CUR"
  - "Cost Category automation"
  - "cost allocation tag activation"
  - "CUR 2.0 split cost allocation"
  - "EKS cost attribution"
  - "BCM Data Exports"
  - "Amazon Q cost analysis"
  - "migrate Cost Explorer to Athena"
  - "CUR chargeback"
routes_to: cur-automation-automator
---

# /aws:automate-cur-automation

Activate the `cur-automation-automator` skill and design an end-to-end
AWS Cost and Usage Report (CUR) automation stack with Athena analytics,
FinOps query automation, QuickSight visualization, Cost Category
chargeback, and CUR 2.0 split cost allocation.

## What it does

Reads a CUR automation scenario (greenfield vs. migration, scope:
single account vs. organization/payer, granularity: hourly vs. daily,
target: Athena-only vs. Athena+QuickSight vs. BCM Data Exports) and
produces a deployment plan with:

1. Pre-flight payer-account gate — verifies the caller is the payer
   (or has cross-account Athena access). Blocks deployment
   (MANUAL_STEP_REQUIRED) on linked-account callers.
2. CUR definition design — hourly granularity with `Resources`
   schema element for resource-level cost, Parquet format,
   `CREATE_NEW` versioning for time-travel queries, KMS-encrypted
   delivery bucket.
3. CUR bucket policy — `billingreports.amazonaws.com` WRITE +
   `athena.amazonaws.com` READ, both with `aws:SourceAccount`
   confused-deputy protection.
4. Athena database + table — partition projection
   (`projection.day.range = '2024/01/01,NOW'`) so MSCK REPAIR TABLE
   is never needed (throttles past ~20k partitions).
5. Athena workgroup — non-`primary` with
   `BytesScannedCutoffPerQuery=1TB` to prevent bill shock.
6. FinOps query automation — named queries: top spenders (service /
   linked account), unused EC2 resources, Savings Plan opportunities,
   RI utilization, tag compliance gaps, EKS pod cost attribution.
7. QuickSight integration — Enterprise edition for scheduled SPICE
   refresh, row-level security by linked account for chargeback.
8. Cost Category automation — `EQUAL`, `PROPORTIONAL`, `FIXED`, or
   `ATTRIBUTES` rules with `Uncategorized` catch-all.
9. Cost allocation tag activation — payer-only API,
   non-backfilling (applies to NEW data only).
10. CUR 2.0 Split Cost Allocation Data (SCAD) — for EKS per-pod cost
    attribution; requires CloudWatch Container Insights on the cluster.
11. BCM Data Exports — modern CUR 2.0 API (`bcm-data-exports`).
12. Amazon Q cost analysis — natural-language layer for ad-hoc
    exploration.

Emits a deterministic VERDICT per stack:

```text
OPERATION: <create | update | audit | migrate-cur2 | add-quicksight | activate-tags | define-cost-categories | enable-bcm-exports>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TARGET: <cur-automation-stack-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <CloudFormation / Terraform template>
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet>
    REASON: <why this cannot be automated>
NOTES: <delivery lag, partition projection caveats, payer-only caveats>
```

## When to invoke

Provide a CUR automation scenario and ask any of:

- "set up CUR with Athena for our payer account"
- "automate our top-spenders query against CUR"
- "build a QuickSight dashboard on top of CUR data"
- "migrate from Cost Explorer to Athena-backed CUR"
- "enable CUR 2.0 split cost allocation for EKS"
- "activate cost allocation tags at scale"
- "set up chargeback with Cost Categories"
- "use BCM Data Exports instead of legacy CUR"
- "wire Amazon Q for natural-language cost analysis"

A bare account + "set up CUR" also routes here via the orchestrator.

## Inputs

- **Required:** caller account type (payer vs. linked), target scope
  (single-account vs. organization), granularity (hourly vs. daily),
  target stack (Athena-only vs. Athena+QuickSight vs. BCM Data Exports).
- **Optional:** CUR bucket name (if existing), Athena workgroup name,
  Cost Category structure, tag keys to activate, QuickSight edition,
  CUR 2.0 SCAD enablement, Amazon Q subscription.

## Outputs

- One VERDICT block per stack (AUTOMATED or MANUAL_STEP_REQUIRED).
- REQUIREMENTS list with [PASS] / [FAIL] per requirement.
- Inline CloudFormation or Terraform template (AUTOMATED) or the
  exact CLI / IaC snippet to close each gap (MANUAL_STEP_REQUIRED).
- NOTES with delivery lag, partition projection caveats, and
  payer-only caveats.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Automate specialist for FinOps cost intelligence).
- `/aws:audit-ce-cost-anomaly` for real-time cost anomaly detection
  (CUR has a 24-hour lag; use CAD for near-real-time alerting).
- `/aws:audit-budgets` for budget enforcement (CUR is informational;
  budgets are alerting).
