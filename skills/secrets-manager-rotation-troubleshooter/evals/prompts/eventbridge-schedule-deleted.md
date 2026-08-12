# Eval prompt: eventbridge-schedule-deleted

Diagnose the Secrets Manager rotation failure for the following secret.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: secret `prod/api/eventbridge-schedule-deleted` has not
rotated in 14 days. There are no rotation Lambda log streams in that
window. RotationEnabled is true and RotationRules shows `rate(1d)`.

```text
SecretId: prod/api/eventbridge-schedule-deleted
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-eventbridge-schedule-deleted
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-21T03:17:22Z
VersionIdsToStages: {"v7": ["AWSCURRENT"]}

Rotation Lambda configuration:
  Timeout: 30
  MemorySize: 256
  Runtime: python3.12
  VpcConfig: correctly attached to DB subnets
  Role: arn:aws:iam::111111111111:role/SecretsManagerRotation-role
  LastModified: 2026-06-15

EventBridge context:
  - aws events list-rules returns NO rule matching
    "SecretsManager" or "eventbridge-schedule-deleted"
  - aws events list-targets-by-rule for any candidate rule
    returns empty
  - aws logs filter-log-events on the rotation Lambda log
    group returns zero events in the last 14 days

Rotation role permissions (verified):
  secretsmanager:GetSecretValue on the secret: ALLOWED
  secretsmanager:PutSecretValue on the secret: ALLOWED
  kms:Decrypt on the CMK: not required (AWS-managed)

Database context: connection succeeds manually from the
rotation Lambda's subnets; rotation role's DB user has
SUPERUSER.
```

A stale `LastRotatedDate` with zero Lambda invocations indicates the
trigger (EventBridge rule) is not firing. Distinguish SCHEDULE_MISSING
(rule absent) from SCHEDULE_DISABLED (rule exists but `State:
DISABLED`). The `events list-rules` output here shows no rule at all
for this secret — the rule was deleted, not disabled.
