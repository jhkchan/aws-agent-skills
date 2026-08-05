# End-to-end usage scenario: wellarchitected-workload-auditor

A walkthrough showing the skill auditing a Well-Architected Tool workload that
is both stale (> 180 days since last review) and has compounding security
HIGH_RISK issues — demonstrating staleness precedence, the effectiveReviewDate
computation, and the re-review-first remediation workflow.

## Input (user prompt)

> Review this Well-Architected Tool workload before our compliance audit next
> week. I want to know if it's in good shape.

```
Today's date: 2026-08-05

Workload id: a1b2c3d4e5f600010203040506070809
Workload name: payments-platform-prod
Workload metadata:
  Environment: PRODUCTION
  Owner: review-team@example.com
  Lenses: ["wellarchitected", "security"]
  LastUpdated: 2026-01-10T08:00:00Z
  ImprovementPlanItems: 4

RiskCounts (aggregate): HIGH_RISK: 3, MEDIUM_RISK: 5, NO_RISK: 10, UNANSWERED: 2

RiskCountsByPillar:
  security:       {HIGH_RISK: 2, MEDIUM_RISK: 1, NO_RISK: 3, UNANSWERED: 0}
  reliability:    {HIGH_RISK: 1, MEDIUM_RISK: 2, NO_RISK: 2, UNANSWERED: 0}
  performance:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 2, UNANSWERED: 0}
  costOptimization: {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 2, UNANSWERED: 1}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 1, UNANSWERED: 0}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 0, UNANSWERED: 1}

Milestones:
  - MilestoneNumber: 1, Name: "Initial baseline review", RecordedAt: 2026-01-10
```

## Skill output

```text
WORKLOAD: payments-platform-prod (a1b2c3d4e5f600010203040506070809)
VERDICT: STALE_REVIEW
REASON: effectiveReviewDate is 2026-01-10 — 207 days ago (> 180 threshold).
The review is stale; the HIGH_RISK findings cannot be trusted as current.
FINDINGS:
  - [STALE_REVIEW] effectiveReviewDate 2026-01-10 is 207 days ago (> 180) (Step 1b)
  - [HIGH_RISK] Security pillar has 2 HIGH_RISK issues — noted but unverified
    due to staleness (Step 2a). These may already be remediated in the live
    infrastructure.
  - [HIGH_RISK] Reliability pillar has 1 HIGH_RISK issue — similarly unverified.
PILLAR_RISK:
  - security: HIGH=2 MED=1 NONE=3 UNANSWERED=0
  - reliability: HIGH=1 MED=2 NONE=2 UNANSWERED=0
  - performance: HIGH=0 MED=1 NONE=2 UNANSWERED=0
  - costOptimization: HIGH=0 MED=1 NONE=2 UNANSWERED=1
  - operationalExcellence: HIGH=0 MED=0 NONE=1 UNANSWERED=0
  - sustainability: HIGH=0 MED=0 NONE=0 UNANSWERED=1
MILESTONES: 1, latest: 2026-01-10 (207 days ago)
REMEDIATION:
  1. Re-run the review — update answers to reflect current architecture.
     aws wellarchitected list-answers --workload-id a1b2c3d4e5f600010203040506070809 \
       --pillar-id security --profile <p>
  2. Create a milestone after the review update to snapshot the new state.
  3. Re-audit after the review is current — the HIGH_RISK findings may no
     longer apply.
```

## What the skill caught that a generic assistant misses

1. **Staleness precedence.** A generic assistant lists the HIGH_RISK findings
   as the top concern. The skill recognises that 207-day-old HIGH_RISK data is
   unreliable — the review must be refreshed before any risk data can be
   trusted. Acting on stale HIGH_RISK wastes remediation effort on phantom
   issues.

2. **effectiveReviewDate computation.** A generic assistant uses `LastUpdated`
   (2026-01-10) directly. The skill explains that `effectiveReviewDate` =
   max(`LastUpdated`, most recent milestone `RecordedAt`) — and in this case
   both are the same date, confirming staleness. If a milestone existed from
   June, the review would be fresher than `LastUpdated` suggests.

3. **Per-pillar risk breakdown.** A generic assistant reports aggregate
   "3 HIGH_RISK issues." The skill breaks it down: 2 in security (exploitable
   attack surface), 1 in reliability (availability risk), 0 in other pillars.
   This prioritisation is invisible in the aggregate number.

4. **Security zero-tolerance vs aggregate threshold.** The skill explains that
   even if the review were fresh, the security HIGH_RISK = 2 would trigger
   HIGH_RISK verdict via rule 2a (zero-tolerance), while the reliability
   HIGH_RISK = 1 alone would not. This distinction guides remediation priority.

## Slash-command invocation

```
/aws:audit-wellarchitected-workload
```

## Live-account follow-up (requires AWS CLI)

```bash
# Re-fetch the workload to confirm staleness
aws wellarchitected describe-workload \
  --workload-id a1b2c3d4e5f600010203040506070809 \
  --profile default --query 'Workload.{LastUpdated:UpdatedAt, RiskCounts:RiskCounts}'

# List milestones to check effectiveReviewDate
aws wellarchitected list-milestones \
  --workload-id a1b2c3d4e5f600010203040506070809 \
  --profile default --query 'MilestoneSummaries[*].{Number:MilestoneNumber, Date:RecordedAt}'

# After re-review, create a milestone
aws wellarchitected create-milestone \
  --workload-id a1b2c3d4e5f600010203040506070809 \
  --milestone-name "Compliance audit refresh 2026-08" \
  --profile default
```
