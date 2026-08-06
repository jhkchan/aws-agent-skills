# Eval prompt: org-trail-no-encryption

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: org-trail-no-encryption
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/org-trail-no-encryption
S3BucketName: org-trail-no-encryption-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: true
  KmsKeyId: null
  LogFileValidationEnabled: true
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:org-trail-no-encryption-cw:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-no-encryption

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  - InsightType: ApiCallRateInsight
  - InsightType: ApiErrorRateInsight

CloudWatch Logs log-group retention: 365 days
