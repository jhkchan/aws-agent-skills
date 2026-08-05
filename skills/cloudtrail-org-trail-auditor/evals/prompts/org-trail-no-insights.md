# Eval prompt: org-trail-no-insights

Audit the following CloudTrail trail configuration. Emit the standard
VERDICT block (TRAIL, VERDICT, REASON, FINDINGS, REMEDIATION).

Trail name: org-trail-no-insights
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/org-trail-no-insights
S3BucketName: org-trail-no-insights-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/org-trail-no-insights-kms
  LogFileValidationEnabled: true
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:org-trail-no-insights-cw:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-no-insights

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  (empty — no selectors configured)

CloudWatch Logs log-group retention: 365 days
