# Eval prompt: healthy-app

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/healthy-app
App name: healthy-app
Current app version: 2
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/well-calibrated-policy

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-006
  assessmentStatus: Success
  appVersion: 2
  startTime: 2026-07-20T08:00:00Z
  endTime: 2026-07-21T10:00:00Z
  complianceScore: 95
  driftStatus: NotDrifted

Resiliency policy (well-calibrated-policy):
  Critical: {RTO: 1 hr, RPO: 15 min}
  Important: {RTO: 4 hr, RPO: 1 hr}
  Standard: {RTO: 24 hr, RPO: 24 hr}

Compliance map (application components):
  api-gateway:        tier=Critical,    complianceStatus=PolicyCompliant
  auth-service:       tier=Critical,    complianceStatus=PolicyCompliant
  user-profile-svc:   tier=Important,   complianceStatus=PolicyCompliant
  notification-svc:   tier=Important,   complianceStatus=PolicyCompliant
  analytics-job:      tier=Standard,    complianceStatus=PolicyCompliant
  report-exporter:    tier=Standard,    complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 3 total, 3 implemented
  SDD:   2 total, 2 implemented
  Test:  1 total, 0 implemented
