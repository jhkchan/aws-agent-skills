# Eval prompt: low-score-standard-tier

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/low-score-standard-tier
App name: low-score-standard-tier
Current app version: 1
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/standard-tier-policy

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-003
  assessmentStatus: Success
  appVersion: 1
  startTime: 2026-07-25T08:00:00Z
  endTime: 2026-07-26T10:00:00Z
  complianceScore: 70
  driftStatus: NotDrifted

Resiliency policy (standard-tier-policy):
  Standard: {RTO: 24 hr, RPO: 24 hr}
  NonCritical: {RTO: 72 hr, RPO: 72 hr}

Compliance map (application components):
  batch-job-a:        tier=Standard,     complianceStatus=PolicyNotCompliant
  batch-job-b:        tier=Standard,     complianceStatus=PolicyNotCompliant
  batch-job-c:        tier=Standard,     complianceStatus=PolicyNotCompliant
  etl-pipeline:       tier=Standard,     complianceStatus=PolicyCompliant
  report-scheduler:   tier=Standard,     complianceStatus=PolicyCompliant
  cache-warmer:       tier=Standard,     complianceStatus=PolicyCompliant
  log-rotator:        tier=NonCritical,  complianceStatus=PolicyCompliant
  data-archiver:      tier=NonCritical,  complianceStatus=PolicyCompliant
  cleanup-task:       tier=NonCritical,  complianceStatus=PolicyCompliant
  sync-worker:        tier=NonCritical,  complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 4 total, 2 implemented
  SDD:   1 total, 1 implemented
  Test:  0 total, 0 implemented
