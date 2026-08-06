# Eval prompt: mission-critical-breach

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/mission-critical-breach
App name: mission-critical-breach
Current app version: 2
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/strict-mc-policy

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-002
  assessmentStatus: Success
  appVersion: 2
  startTime: 2026-07-30T08:00:00Z
  endTime: 2026-07-31T10:00:00Z
  complianceScore: 75
  driftStatus: NotDrifted

Resiliency policy (strict-mc-policy):
  MissionCritical: {RTO: 5 min, RPO: 5 min}
  Critical: {RTO: 1 hr, RPO: 15 min}
  Standard: {RTO: 24 hr, RPO: 24 hr}

Compliance map (application components):
  checkout-api:       tier=MissionCritical, complianceStatus=PolicyNotCompliant
  inventory-svc:      tier=MissionCritical, complianceStatus=PolicyCompliant
  fraud-detection:    tier=Critical,         complianceStatus=PolicyCompliant
  payment-gateway:    tier=Critical,         complianceStatus=PolicyCompliant
  email-dispatcher:   tier=Standard,          complianceStatus=PolicyCompliant
  report-generator:   tier=Standard,          complianceStatus=PolicyNotCompliant
  batch-loader:       tier=Standard,          complianceStatus=PolicyCompliant
  cleanup-cron:       tier=Standard,          complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 3 total, 1 implemented
  SDD:   2 total, 1 implemented
  Test:  1 total, 0 implemented
