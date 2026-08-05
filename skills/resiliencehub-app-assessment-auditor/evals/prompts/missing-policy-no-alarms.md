# Eval prompt: missing-policy-no-alarms

Audit the following AWS Resilience Hub application assessment for resiliency
posture. Emit the standard VERDICT block (APP, VERDICT, REASON, FINDINGS,
REMEDIATION).

Today's date: 2026-08-05

App ARN: arn:aws:resiliencehub:us-east-1:111111111111:app/missing-policy-no-alarms
App name: missing-policy-no-alarms
Current app version: 1
App policyArn (attached): null (no policy bound to this app)

Latest assessment:
  assessmentArn: arn:aws:resiliencehub:us-east-1:111111111111:app-assessment/assess-004
  assessmentStatus: Success
  appVersion: 1
  startTime: 2026-07-29T08:00:00Z
  endTime: 2026-07-30T10:00:00Z
  complianceScore: 88
  driftStatus: NotDrifted
  policy.policyArn (ad-hoc policy used for this assessment): arn:aws:resiliencehub:us-east-1:111111111111:resiliency-policy/adhoc-assessment-policy

Ad-hoc policy used for this assessment:
  Important: {RTO: 4 hr, RPO: 1 hr}
  Standard: {RTO: 24 hr, RPO: 24 hr}

Compliance map (application components):
  content-api:        tier=Important,  complianceStatus=PolicyCompliant
  media-processor:    tier=Important,  complianceStatus=PolicyCompliant
  thumbnail-svc:      tier=Standard,   complianceStatus=PolicyCompliant
  search-indexer:     tier=Standard,   complianceStatus=PolicyCompliant
  upload-handler:     tier=Standard,   complianceStatus=PolicyCompliant
  metadata-cleanup:   tier=Standard,   complianceStatus=PolicyCompliant
  transcode-worker:   tier=Standard,   complianceStatus=PolicyCompliant
  delivery-cache:     tier=Standard,   complianceStatus=PolicyCompliant

Recommendations:
  Alarm: 3 total, 0 implemented
  SDD:   1 total, 1 implemented
  Test:  0 total, 0 implemented
