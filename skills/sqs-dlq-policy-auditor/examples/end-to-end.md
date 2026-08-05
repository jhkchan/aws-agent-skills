# End-to-end usage scenario: sqs-dlq-policy-auditor

A walkthrough showing the skill auditing a production SQS queue that has
public access via a wildcard Principal (CRITICAL) while also having a DLQ
configured and encryption enabled, demonstrating severity aggregation, the
Principal:"*" + SourceArn distinction, and the per-verdict CLI remediation
workflow.

## Input (user prompt)

> We need to harden our order-processing SQS queue before the holiday
> traffic surge. Here is the current configuration. What needs fixing?

```json
{
  "QueueUrl": "https://sqs.us-east-1.amazonaws.com/111111111111/order-processing",
  "QueueArn": "arn:aws:sqs:us-east-1:111111111111:order-processing",
  "Attributes": {
    "Policy": {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "LegacyOpenAccess",
          "Effect": "Allow",
          "Principal": "*",
          "Action": "sqs:SendMessage",
          "Resource": "arn:aws:sqs:us-east-1:111111111111:order-processing"
        },
        {
          "Sid": "S3EventNotification",
          "Effect": "Allow",
          "Principal": "*",
          "Action": "sqs:SendMessage",
          "Resource": "arn:aws:sqs:us-east-1:111111111111:order-processing",
          "Condition": {
            "ArnEquals": {"aws:SourceArn": "arn:aws:s3:::order-upload-bucket"}
          }
        }
      ]
    },
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:111111111111:order-processing-dlq\",\"maxReceiveCount\":\"5\"}",
    "SqsManagedSseEnabled": true,
    "MessageRetentionPeriod": "345600",
    "VisibilityTimeout": "30"
  },
  "DLQAttributes": {
    "QueueArn": "arn:aws:sqs:us-east-1:111111111111:order-processing-dlq",
    "MessageRetentionPeriod": "86400"
  }
}
```

## Skill output

```text
QUEUE: https://sqs.us-east-1.amazonaws.com/111111111111/order-processing
VERDICT: PUBLIC_ACCESS
REASON: Queue policy Statement "LegacyOpenAccess" grants sqs:SendMessage to
  Principal:"*" with no restrictive condition — any AWS account can inject
  messages into the order-processing queue (Step 1).
RISK: CRITICAL
FINDINGS:
  - [CRITICAL] Principal:"*" + sqs:SendMessage with no condition in Statement
    "LegacyOpenAccess" (Step 1) — any account can poison the order queue
  - [OK] Statement "S3EventNotification" — Principal:"*" with aws:SourceArn
    condition (S3 notification pattern); NOT public (Step 1 strong-condition
    exemption)
  - [OK] RedrivePolicy configured with maxReceiveCount=5 (Step 2)
  - [OK] SSE-SQS encryption enabled (Step 3)
  - [MEDIUM] DLQ MessageRetentionPeriod is 86400 (1 day) — insufficient time
    for analysis; recommend 1209600 (14 days) (Step 4c)
REMEDIATION:
  1. CRITICAL — Remove the "LegacyOpenAccess" statement immediately. Back up
     the policy first:
     aws sqs get-queue-attributes --queue-url <url> \
       --attribute-names Policy --output json > /tmp/order-processing-policy-backup.json
  2. CRITICAL — Assume breach. Audit CloudTrail for sqs:SendMessage from
     unexpected principals during the exposure window. Messages may have been
     injected — verify order integrity.
  3. MEDIUM – Set the DLQ retention to 14 days:
     aws sqs set-queue-attributes --queue-url <dlq-url> \
       --attributes MessageRetentionPeriod=1209600
  4. Keep the "S3EventNotification" statement — the aws:SourceArn condition
     makes it safe (S3 bucket scoped).
```

## What the skill caught that a generic assistant misses

1. **Two statements with Principal:"*" — one public, one safe.** A generic
   assistant sees both `Principal: "*"` statements and flags the entire
   queue as "public." The skill distinguishes: "LegacyOpenAccess" has NO
   condition (CRITICAL), while "S3EventNotification" has `aws:SourceArn`
   (the standard S3-to-SQS pattern — safe). The remediation removes only
   the dangerous statement, preserving the S3 integration.

2. **Severity aggregation with per-finding breakdown.** The verdict is
   PUBLIC_ACCESS (worst finding), but the FINDINGS list shows the
   individual dimensions: the open policy is CRITICAL, the S3 notification
   statement is OK, the DLQ config is OK, and the DLQ retention gap is
   MEDIUM. The operator can triage each finding independently.

3. **The DLQ retention advisory.** Even though the DLQ is configured, its
   1-day retention period is flagged as a CONFIG_GAP — failed orders
   expire before the team can investigate during a holiday weekend.

4. **The assume-breach remediation.** Generic advice says "remove the
   access." The skill's remediation includes auditing CloudTrail for
   `sqs:SendMessage` events from unexpected principals — because injected
   orders may have already compromised the order pipeline.

## Slash-command invocation

```
/aws:audit-sqs-dlq-policy
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our order-processing SQS queue before the holiday surge"
```

The orchestrator emits
`[Phase: Audit | Skills routed: sqs-dlq-policy-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this SQS queue for DLQ and public access"
# [Phase: Audit | Skills routed: sqs-dlq-policy-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the queue posture:

```bash
# Verify the wildcard statement was removed
aws sqs get-queue-attributes --queue-url <url> \
  --attribute-names Policy --profile default \
  | jq '.Attributes.Policy | fromjson | .Statement[] | .Sid'

# Confirm DLQ retention is 14 days
aws sqs get-queue-attributes --queue-url <dlq-url> \
  --attribute-names MessageRetentionPeriod --profile default

# Check for messages in the DLQ
aws sqs get-queue-attributes --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages --profile default
```

Then monitor CloudTrail for `sqs:SendMessage` events from unexpected
principals for 1-2 weeks.
