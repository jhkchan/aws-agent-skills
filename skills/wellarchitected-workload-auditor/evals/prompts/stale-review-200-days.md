# Eval prompt: stale-review-200-days

Audit the following AWS Well-Architected Tool workload for review health. Emit
the standard VERDICT block (WORKLOAD, VERDICT, REASON, FINDINGS, PILLAR_RISK,
MILESTONES, REMEDIATION).

Today's date: 2026-08-05

Workload id: a1b2c3d4e5f600010203040506070809
Workload name: stale-review-200-days
Workload metadata:
  Environment: PRODUCTION
  Owner: review-team@example.com
  Lenses: ["wellarchitected", "security"]
  PillarPriorities: ["security", "reliability", "operationalExcellence", "performance", "costOptimization", "sustainability"]
  ArchitecturalDesign: "Three-tier web application with RDS Multi-AZ and ElastiCache."
  CreatedAt: 2025-06-01
  LastUpdated: 2026-01-10T08:00:00Z
  ImprovementPlanItems: 4

RiskCounts (aggregate across all pillars):
  HIGH_RISK: 3
  MEDIUM_RISK: 5
  NO_RISK: 10
  NOT_APPLICABLE: 2
  UNANSWERED: 2

RiskCountsByPillar:
  security:       {HIGH_RISK: 2, MEDIUM_RISK: 1, NO_RISK: 3, UNANSWERED: 0}
  reliability:    {HIGH_RISK: 1, MEDIUM_RISK: 2, NO_RISK: 2, UNANSWERED: 0}
  performance:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 2, UNANSWERED: 0}
  costOptimization: {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 2, UNANSWERED: 1}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 1, UNANSWERED: 0}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 0, UNANSWERED: 1}

Milestones:
  - MilestoneNumber: 1, Name: "Initial baseline review", RecordedAt: 2026-01-10
