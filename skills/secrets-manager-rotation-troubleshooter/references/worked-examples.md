# Worked Examples — Secrets Manager Rotation Troubleshooter

Secondary worked examples and re-prompt templates moved out of the SKILL.md body. Loaded on demand.


## Malformed / missing input — INSUFFICIENT_DATA re-prompt template
```text
TARGET: <secret-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the rotation Lambda error or observed behaviour such
  as "LastRotatedDate is 7 days old") and the SecretId.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact SecretId or
  ARN, (2) the observed symptom (rotation Lambda error log line,
  stale LastRotatedDate, or application connection failures after
  rotation), and (3) for live diagnosis, the rotation Lambda name
  and recent CloudWatch log stream.
```

## Worked example — SCHEDULE_MISSING (EventBridge rule deleted)

```text
TARGET: prod/api/github-webhook-token
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RotationRules.ScheduleExpression is rate(1d) and
  RotationEnabled is true, but the EventBridge rule
  SecretsManager-prod-api-github-webhook-token does not exist.
  No rotation has fired in 14 days; LastRotatedDate is 2026-07-21.
LAYER: SCHEDULE_MISSING
EVIDENCE:
  - Symptom: LastRotatedDate is 2026-07-21; today is 2026-08-05.
  - Probe: aws events list-rules returns no rule matching the
    rotation Lambda's ARN as target.
  - Probe: aws logs filter-log-events on the rotation Lambda's log
    group returns zero events in the last 14 days.
  - Passing: rotation Lambda configuration is intact (Timeout=30,
    VpcConfig correct, role has GetSecretValue); the rotation role
    has not been modified since 2026-06-15.
REMEDIATION:
  1. Recreate the EventBridge rule with the rotation Lambda as
     target:
     aws events put-rule --name SecretsManager-prod-api-github-webhook-token \
       --schedule-expression "rate(1d)" --state ENABLED --profile <p>
     aws events put-targets --rule SecretsManager-prod-api-github-webhook-token \
       --targets '{"Id":"1","Arn":"<rotation-lambda-arn>"}' --profile <p>
  2. Add the resource-based permission for EventBridge to invoke the
     Lambda:
     aws lambda add-permission --function-name <rotation-lambda-name> \
       --statement-id EventBridgeInvoke --action lambda:InvokeFunction \
       --principal events.amazonaws.com \
       --source-arn arn:aws:events:<region>:<account>:rule/SecretsManager-prod-api-github-webhook-token \
       --profile <p>
  3. Trigger a manual rotation to verify the end-to-end path:
     aws secretsmanager rotate-secret --secret-id prod/api/github-webhook-token \
       --profile <p>
CONFIRM: Before recreating the rule, emit and await:
  "CONFIRM: About to recreate EventBridge rule
   SecretsManager-prod-api-github-webhook-token targeting
   <rotation-lambda>. Proceed? (yes/no)"
```

## Worked example — INSUFFICIENT_DATA

```text
TARGET: prod/auth/oauth-signing-key
VERDICT: INSUFFICIENT_DATA
REASON: The rotation Lambda's recent logs show a database connection
  error, but the secret's connection string (host, port, dbname) was
  not provided and the rotation Lambda's environment variables cannot
  be read without its name.
LAYER: UNKNOWN
EVIDENCE:
  - Observed: "LastRotatedDate is 2026-07-30; rotation Lambda logs
    'Could not connect to database'."
  - Missing: rotation Lambda name or ARN, secret value's connection
    keys (host/port/dbname), RDS instance identifier.
REMEDIATION: Re-prompt the operator for: (1) the rotation Lambda name
  or ARN (visible in describe-secret.RotationLambdaARN), (2) the
  database instance identifier (to cross-reference host/port), and
  (3) the rotation Lambda's recent CloudWatch log stream around the
  failing setSecret step.
```
