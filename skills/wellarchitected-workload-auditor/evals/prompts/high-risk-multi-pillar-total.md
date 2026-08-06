# Eval prompt: high-risk-multi-pillar-total

Audit the following AWS Well-Architected Tool workload for review health. Emit
the standard VERDICT block (WORKLOAD, VERDICT, REASON, FINDINGS, PILLAR_RISK,
MILESTONES, REMEDIATION).

Today's date: 2026-08-05

Workload id: e5f60413234244454647484950515260
Workload name: high-risk-multi-pillar-total
Workload metadata:
  Environment: PRODUCTION
  Owner: ops-team@example.com
  Lenses: ["wellarchitected", "security", "costOptimization"]
  PillarPriorities: ["security", "reliability", "operationalExcellence", "performance", "costOptimization", "sustainability"]
  ArchitecturalDesign: "Multi-AZ EC2 auto-scaling group with Redis cache and S3 data lake."
  CreatedAt: 2025-06-01
  LastUpdated: 2026-06-10T08:00:00Z
  ImprovementPlanItems: 6

RiskCounts (aggregate across all pillars):
  HIGH_RISK: 6
  MEDIUM_RISK: 7
  NO_RISK: 12
  NOT_APPLICABLE: 1
  UNANSWERED: 2

RiskCountsByPillar:
  security:       {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 5, UNANSWERED: 0}
  reliability:    {HIGH_RISK: 3, MEDIUM_RISK: 2, NO_RISK: 1, UNANSWERED: 1}
  performance:    {HIGH_RISK: 2, MEDIUM_RISK: 2, NO_RISK: 2, UNANSWERED: 0}
  costOptimization: {HIGH_RISK: 1, MEDIUM_RISK: 2, NO_RISK: 2, UNANSWERED: 0}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 1, UNANSWERED: 1}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 1, UNANSWERED: 0}

Milestones:
  - MilestoneNumber: 1, Name: "Initial review", RecordedAt: 2026-06-10
