# Eval prompt: stale-95-days

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/stale-95-days
App name: stale-95-days
Current app version: 3
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/prod-mc-policy

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-001
  assessmentStatus: Success
  appVersion: 3
  startTime: 2026-05-01T08:00:00Z
  endTime: 2026-05-02T10:00:00Z
  complianceScore: 85
  driftStatus: NotChecked

Resiliency policy (prod-mc-policy):
  MissionCritical: {RTO: 5 min, RPO: 5 min}
  Standard: {RTO: 24 hr, RPO: 24 hr}

Compliance map (application components):
  payment-api:        tier=MissionCritical, complianceStatus=PolicyCompliant
  auth-service:       tier=MissionCritical, complianceStatus=PolicyCompliant
  order-processor:    tier=MissionCritical, complianceStatus=PolicyCompliant
  reporting-job:      tier=Standard,          complianceStatus=PolicyNotCompliant
  notifications-svc:  tier=Standard,          complianceStatus=PolicyCompliant
  data-sync-lambda:   tier=Standard,          complianceStatus=PolicyCompliant
  audit-logger:       tier=Standard,          complianceStatus=PolicyCompliant
  health-check:       tier=Standard,          complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 2 total, 2 implemented
  SDD:   1 total, 1 implemented
  Test:  1 total, 0 implemented
