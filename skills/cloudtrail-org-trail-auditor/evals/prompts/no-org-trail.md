# Eval prompt: no-org-trail

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: no-org-trail
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/no-org-trail
S3BucketName: no-org-trail-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: false
  IsMultiRegionTrail: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/no-org-trail-kms
  LogFileValidationEnabled: true
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:no-org-trail-cw:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-no-org-trail

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  - InsightType: ApiCallRateInsight
  - InsightType: ApiErrorRateInsight

CloudWatch Logs log-group retention: 365 days
