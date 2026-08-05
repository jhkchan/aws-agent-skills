# Eval prompt: failed-assessment-no-data

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/failed-assessment-no-data
App name: failed-assessment-no-data
Current app version: 2
App policyArn (attached): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/prod-policy

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-005
  assessmentStatus: Failed
  appVersion: 2
  startTime: 2026-07-29T08:00:00Z
  endTime: 2026-07-30T10:00:00Z
  complianceScore: null (no data — assessment failed)
  compliance map: empty (no components assessed)
  driftStatus: NotChecked

Resiliency policy (prod-policy):
  MissionCritical: {RTO: 5 min, RPO: 5 min}
  Standard: {RTO: 24 hr, RPO: 24 hr}

No compliance map or recommendation data is available because the
assessment did not complete successfully.
