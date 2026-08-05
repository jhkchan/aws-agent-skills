---
description: Audit a Well-Architected Tool workload for review staleness, per-pillar high-risk issues, milestone tracking gaps, and remediation plan completeness.
nl_triggers:
  - "audit this Well-Architected workload"
  - "check WA review freshness"
  - "Well-Architected review stale"
  - "high-risk issues per pillar"
  - "milestone tracking gaps"
  - "Well-Architected workload health"
  - "review staleness check"
  - "UNANSWERED questions Well-Architected"
  - "remediation plan tracking"
  - "workload review audit"
  - "Well-Architected compliance gate"
  - "effectiveReviewDate"
  - "lens coverage gap"
routes_to: wellarchitected-workload-auditor
---

# /aws:audit-wellarchitected-workload

Activate the `wellarchitected-workload-auditor` skill and audit one or more
Well-Architected Tool workloads for review health and configuration gaps.

## What it does

Reads workload metadata (Environment, Lenses, LastUpdated), aggregate
RiskCounts, per-pillar RiskCountsByPillar, milestone history, and improvement
plan items, then applies the ordered classification logic:

1. **Staleness (STALE_REVIEW)** — highest priority. effectiveReviewDate >
   180 days, or no milestones + > 90 days, or UNANSWERED > 50%.
2. **High-risk (HIGH_RISK)** — security pillar HIGH_RISK > 0 (zero-tolerance),
   or total HIGH_RISK across all pillars > 5.
3. **Configuration gap (CONFIG_GAP)** — no milestones, only default lens,
   or Environment not set.
4. **OK** — all checks pass.

Emits a deterministic VERDICT per workload:

```text
WORKLOAD: <name> (<id>)
VERDICT: STALE_REVIEW | HIGH_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [STALE_REVIEW] <description (Step Nb)>
  - [HIGH_RISK] <description (Step Na)>
PILLAR_RISK:
  - security: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - reliability: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - ...
MILESTONES: <count>, latest: <date> (<n> days ago)
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Well-Architected workload configuration and ask any of:

- "audit this Well-Architected workload"
- "is my WA review stale?"
- "check high-risk issues per pillar"
- "how many milestones do I have?"
- "is my workload review healthy?"
- "check remediation plan completeness"

A workload ID plus any audit verb also routes here.

## Inputs

- Workload metadata: Environment, Owner, Lenses, PillarPriorities,
  LastUpdated, CreatedAt, ImprovementPlanItems.
- RiskCounts (aggregate) and RiskCountsByPillar (per-pillar breakdown).
- Milestone list: MilestoneNumber, Name, RecordedAt.
- For live-account audits: workload ID for `describe-workload` +
  `list-milestones` + `list-answers` per pillar.

## Outputs

- One VERDICT block per workload.
- Enumerated FINDINGS list with per-finding severity and step citation.
- Per-pillar risk breakdown for all six pillars.
- Milestone count and most recent date with day-delta.
- Specific remediation: re-run review, create milestone, apply lens, set
  environment, update answers.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Well-Architected governance).
- `/aws:audit-kms-key-policy` for encryption-key posture that may relate
  to WA security-pillar findings.
