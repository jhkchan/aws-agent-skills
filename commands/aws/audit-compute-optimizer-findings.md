---
description: Audit Compute Optimizer findings for EC2, EBS, Lambda, and ASG resources — classifies overprovisioned waste, underprovisioned risk, and low-confidence findings into UNDERUTILIZED/NOT_OPTIMIZED/OK with per-finding risk and CLI remediation.
nl_triggers:
  - "audit compute optimizer findings"
  - "check EC2 right-sizing recommendations"
  - "compute optimizer recommendations"
  - "is this compute optimizer finding reliable"
  - "overprovisioned EC2 instances"
  - "underutilized resources"
  - "Lambda memory recommendations"
  - "EBS volume recommendations"
  - "performanceRisk too high"
  - "right-size EC2 instances"
  - "compute optimizer low confidence"
  - "inferred memory finding"
  - "stale compute optimizer finding"
  - "compute optimizer enrollment check"
routes_to: compute-optimizer-findings-auditor
---

# /aws:audit-compute-optimizer-findings

Activate the `compute-optimizer-findings-auditor` skill and audit one or more
Compute Optimizer findings for EC2, EBS, Lambda, or Auto Scaling Group
resources.

## What it does

Reads a Compute Optimizer finding document (finding, findingReasons,
utilizationMetrics, recommendationOptions) and applies the ordered
classification logic:

1. Pre-flight — enrollment check, data sufficiency, stale finding detection.
2. Confidence evaluation — gates the verdict based on metric completeness
   (CWAgent memory data for EC2), performanceRisk on recommendations, and
   invocation data for Lambda.
3. Finding classification:
   - Overprovisioned + HIGH confidence → UNDERUTILIZED (actionable waste)
   - Overprovisioned + LOW confidence → NOT_OPTIMIZED (unreliable, do not act)
   - Underprovisioned → NOT_OPTIMIZED (performance risk)
   - Optimized → OK
4. Risk severity based on utilization levels and savings opportunity.
5. Aggregation — worst finding wins across resources.

Emits a deterministic VERDICT per resource:

```text
RESOURCE: <arn or resource-id>
VERDICT: UNDERUTILIZED | NOT_OPTIMIZED | OK
REASON: <1-2 sentences citing the finding, confidence, and key metric>
RISK: HIGH | MEDIUM | LOW
FINDINGS:
  - [<severity>] <finding description with rule citation>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Compute Optimizer finding and ask any of:

- "audit this compute optimizer finding"
- "should I act on this EC2 right-sizing recommendation?"
- "is this overprovisioned finding reliable?"
- "what's the risk of this performanceRisk 4 recommendation?"
- "check these Lambda memory recommendations"
- "are these EBS volume recommendations actionable?"

A bare resource ARN + any audit verb ("audit this instance finding",
"check these recommendations") also routes here via the orchestrator.

## Inputs

- A Compute Optimizer finding/recommendation document for EC2, EBS, Lambda,
  or ASG: finding field, findingReasons, utilizationMetrics (with source —
  CloudWatch vs CloudWatchAgent vs inferred), recommendationOptions (with
  performanceRisk and savingsOpportunity), and lastRefreshTimestamp.
- For live-account audits: a resource ARN or "all findings" request. The
  skill reads from `aws compute-optimizer get-*-recommendations` APIs.

## Outputs

- One VERDICT block per resource.
- Confidence-gated classification: low-confidence findings are NOT_OPTIMIZED,
  not UNDERUTILIZED — the skill refuses to recommend action on unreliable data.
- Per-finding risk level with savings quantification.
- CLI remediation commands per verdict (EC2 stop/modify/start, Lambda
  update-function-configuration, EBS modify-volume, ASG instance-refresh).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Compute cost optimization).
- `/aws:audit-ec2-security-groups` for security-group exposure audits on
  the same EC2 instances.
