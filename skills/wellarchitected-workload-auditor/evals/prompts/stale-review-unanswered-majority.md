# Eval prompt: stale-review-unanswered-majority

Audit the following AWS Well-Architected Tool workload for review health. Emit
the standard VERDICT block (WORKLOAD, VERDICT, REASON, FINDINGS, PILLAR_RISK,
MILESTONES, REMEDIATION).

Today's date: 2026-08-05

Workload id: f6051423524546474849505152535460
Workload name: stale-review-unanswered-majority
Workload metadata:
  Environment: PREPRODUCTION
  Owner: qa-team@example.com
  Lenses: ["wellarchitected", "security"]
  PillarPriorities: ["security", "reliability", "operationalExcellence", "performance", "costOptimization", "sustainability"]
  ArchitecturalDesign: "Staging environment for the payments platform."
  CreatedAt: 2026-06-01
  LastUpdated: 2026-07-28T08:00:00Z
  ImprovementPlanItems: 0

RiskCounts (aggregate across all pillars):
  HIGH_RISK: 0
  MEDIUM_RISK: 4
  NO_RISK: 5
  NOT_APPLICABLE: 1
  UNANSWERED: 12

RiskCountsByPillar:
  security:       {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 2, UNANSWERED: 4}
  reliability:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 1, UNANSWERED: 3}
  performance:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 1, UNANSWERED: 2}
  costOptimization: {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 1, UNANSWERED: 1}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 0, UNANSWERED: 1}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 0, UNANSWERED: 1}

Milestones:
  - MilestoneNumber: 1, Name: "Kickoff review", RecordedAt: 2026-07-28
