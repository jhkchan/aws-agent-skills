# Eval prompt: org-trail-ok

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: org-trail-ok
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/org-trail-ok
S3BucketName: org-trail-ok-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/org-trail-ok-kms-key
  LogFileValidationEnabled: true
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:cloudtrail-org-trail-ok:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-org-trail-ok

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  - InsightType: ApiCallRateInsight
  - InsightType: ApiErrorRateInsight

CloudWatch Logs log-group retention: 365 days
