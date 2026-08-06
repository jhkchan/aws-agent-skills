# Eval prompt: org-trail-config-gap

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: org-trail-config-gap
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/org-trail-config-gap
S3BucketName: org-trail-config-gap-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: false
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/org-trail-config-gap-kms
  LogFileValidationEnabled: true
  IncludeGlobalServiceEvents: false
  CloudWatchLogsLogGroupArn: null
  CloudWatchLogsRoleArn: null

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  - InsightType: ApiCallRateInsight
  - InsightType: ApiErrorRateInsight

CloudWatch Logs log-group retention: N/A (no log group configured)
