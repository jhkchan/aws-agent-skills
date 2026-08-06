# Eval prompt: high-risk-security-pillar

Audit the following AWS Well-Architected Tool workload for review health. Emit
the standard VERDICT block (WORKLOAD, VERDICT, REASON, FINDINGS, PILLAR_RISK,
MILESTONES, REMEDIATION).

Today's date: 2026-08-05

Workload id: b2c3d4e5f60111213141516171819101
Workload name: high-risk-security-pillar
Workload metadata:
  Environment: PRODUCTION
  Owner: platform-team@example.com
  Lenses: ["wellarchitected", "security", "reliability"]
  PillarPriorities: ["security", "reliability", "performance", "operationalExcellence", "costOptimization", "sustainability"]
  ArchitecturalDesign: "Containerized microservices on EKS with Aurora PostgreSQL."
  CreatedAt: 2025-03-01
  LastUpdated: 2026-07-10T08:00:00Z
  ImprovementPlanItems: 8

RiskCounts (aggregate across all pillars):
  HIGH_RISK: 5
  MEDIUM_RISK: 8
  NO_RISK: 15
  NOT_APPLICABLE: 1
  UNANSWERED: 1

RiskCountsByPillar:
  security:       {HIGH_RISK: 5, MEDIUM_RISK: 2, NO_RISK: 5, UNANSWERED: 0}
  reliability:    {HIGH_RISK: 0, MEDIUM_RISK: 2, NO_RISK: 3, UNANSWERED: 1}
  performance:    {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 3, UNANSWERED: 0}
  costOptimization: {HIGH_RISK: 0, MEDIUM_RISK: 2, NO_RISK: 2, UNANSWERED: 0}
  operationalExcellence: {HIGH_RISK: 0, MEDIUM_RISK: 1, NO_RISK: 1, UNANSWERED: 0}
  sustainability: {HIGH_RISK: 0, MEDIUM_RISK: 0, NO_RISK: 1, UNANSWERED: 0}

Milestones:
  - MilestoneNumber: 1, Name: "Initial review", RecordedAt: 2026-03-15
  - MilestoneNumber: 2, Name: "Post-remediation snapshot", RecordedAt: 2026-07-10
