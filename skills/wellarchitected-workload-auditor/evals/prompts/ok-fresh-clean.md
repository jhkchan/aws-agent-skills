# Eval prompt: ok-fresh-clean

Audit the following AWS Well-Architected Tool workload for review health. Emit
the standard VERDICT block (WORKLOAD, VERDICT, REASON, FINDINGS, PILLAR_RISK,
MILESTONES, REMEDIATION).

Today's date: 2026-08-05

Workload id: d4e5f6031223334353637383930415060
Workload name: ok-fresh-clean
Workload metadata:
  Environment: PRODUCTION
  Owner: architecture-team@example.com
  Lenses: ["wellarchitected", "security", "reliability", "costOptimization"]
  PillarPriorities: ["security", "reliability", "operationalExcellence", "performance", "costOptimization", "sustainability"]
  ArchitecturalDesign: "Serverless event-driven pipeline with Lambda, EventBridge, and DynamoDB."
  CreatedAt: 2025-01-01
  LastUpdated: 2026-06-25T08:00:00Z
  ImprovementPlanItems: 3

RiskCounts (aggregate across all pillars):
  HIGH_RISK: 0
  MEDIUM_RISK: 1
  NO_RISK: 22
  NOT_APPLICABLE: 0
  UNANSWERED: 0

RiskCountsByPillar:
  security:       {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 5, UNANSWERED: 0}
  reliability:    {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 4, UNANSWERED: 0}
  performance:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 3, UNANSWERED: 0}
  costOptimization: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 4, UNANSWERED: 0}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 4, UNANSWERED: 0}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 2, UNANSWERED: 0}

Milestones:
  - MilestoneNumber: 1, Name: "Q1 baseline", RecordedAt: 2026-01-15
  - MilestoneNumber: 2, Name: "Q2 review", RecordedAt: 2026-04-10
  - MilestoneNumber: 3, Name: "Post-audit", RecordedAt: 2026-06-25
