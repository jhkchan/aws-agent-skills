# Eval prompt: org-trail-no-validation

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: org-trail-no-validation
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/org-trail-no-validation
S3BucketName: org-trail-no-validation-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/org-trail-no-validation-kms
  LogFileValidationEnabled: false
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:org-trail-no-validation-cw:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-no-validation

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  - InsightType: ApiCallRateInsight
  - InsightType: ApiErrorRateInsight

CloudWatch Logs log-group retention: 365 days
