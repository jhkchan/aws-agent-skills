# End-to-end usage scenario: eventbridge-bus-policy-auditor

A walkthrough showing the skill auditing a custom EventBridge event bus
that has a wildcard PutEvents grant (PUBLIC_BUS), missing dead-letter
queues (NO_DLQ), and no customer-managed KMS key (NO_ENCRYPTION),
demonstrating severity aggregation, the event-injection concept, and
per-finding remediation.

## Input (user prompt)

> Review this EventBridge bus before we go to production. It handles
> our order-processing pipeline — Lambda and SQS targets.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "events:*",
      "Resource": "*"
    },
    {
      "Sid": "PartnerIngest",
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/orders-bus-prod"
    }
  ]
}
```

Bus metadata:
- KmsKeyIdentifier: (absent)

Rules:
- order-processing-rule: targets Lambda + SQS (no DeadLetterConfig)

Archive: (none)

## Skill output

```text
BUS: orders-bus-prod
VERDICT: PUBLIC_BUS
REASON: Statement "PartnerIngest" grants events:PutEvents to Principal
"*" with no restrictive condition — any AWS account holder can inject
events that trigger every rule on the bus (Step 5a). Rule targets also
lack dead-letter queues and no customer-managed KMS key is configured.
FINDINGS:
  - [PUBLIC_BUS] Principal "*" + events:PutEvents + no condition (Step 5a)
    — event injection: one permission drives every rule and downstream
    target (Lambda, SQS, Step Functions)
  - [NO_DLQ] Rule "order-processing-rule" targets "lambda-target" and
    "sqs-target" have no DeadLetterConfig (Step 6) — failed invocations
    silently dropped after ~6h retry window
  - [NO_ENCRYPTION] KmsKeyIdentifier absent — bus uses AWS-owned key
    with no rotation control or decrypt-audit capability (Step 7)
  - [CONFIG_GAP] No archive configured — no replay capability for
    incident recovery (Step 8)
  - [OK] Statement "RootAccess" — normal root-delegation pattern,
    not flagged (Step 5g)
REMEDIATION:
  1. PUBLIC_BUS — Replace Principal "*" with the specific partner
     account/role ARN. Add aws:SourceAccount condition:
     aws events put-permission --event-bus-name orders-bus-prod
       --action events:PutEvents
       --principal arn:aws:iam::222222222222:role/partner-publisher
       --statement-id PartnerScoped
       --condition '{"Type":"StringEquals","Key":"aws:SourceAccount","Value":"222222222222"}'
     Then remove the wildcard:
     aws events remove-permission --event-bus-name orders-bus-prod
       --statement-id PartnerIngest
  2. PUBLIC_BUS — Assume breach. Audit CloudTrail for events:PutEvents
     from unexpected principals. Check Lambda/SQS for anomalous
     invocations triggered by injected events.
  3. NO_DLQ — Create a DLQ and attach to each target:
     aws sqs create-queue --queue-name orders-bus-dlq
     aws events put-targets --rule order-processing-rule
       --event-bus-name orders-bus-prod
       --targets '[{"Id":"lambda-target","Arn":"arn:aws:lambda:us-east-1:111111111111:function:order-handler","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:orders-bus-dlq"}},{"Id":"sqs-target","Arn":"arn:aws:sqs:us-east-1:111111111111:order-queue","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:orders-bus-dlq"}}]'
  4. NO_ENCRYPTION — Associate a CMK:
     aws events update-event-bus --name orders-bus-prod
       --kms-key-identifier arn:aws:kms:us-east-1:111111111111:key/cmk-orders
  5. CONFIG_GAP — Create an archive:
     aws events create-archive --archive-name orders-archive
       --event-source-name orders-bus-prod --retention 30
  6. Back up the policy before changes:
     aws events describe-event-bus --name orders-bus-prod --output json
       > /tmp/orders-bus-policy-backup.json
```

## What the skill caught that a generic assistant misses

1. **The events:PutEvents blast-radius multiplier.** A generic assistant
   says "wildcard access is risky." The skill explains that PutEvents is
   an event-injection vector — one permission can drive every rule on
   the bus, triggering Lambda, Step Functions, SQS, and API destinations.
   The blast radius extends through the entire event-driven pipeline.

2. **The root-delegation statement is NOT flagged.** The `Principal: root`
   + `events:*` statement is the default IAM-delegation pattern. A naive
   auditor flags it as "wildcard events:* access." The skill recognises
   it as NORMAL (Step 5g) and excludes it from the verdict.

3. **DeadLetterConfig is per-TARGET, not per-rule.** A generic assistant
   might say "add a DLQ to the rule." The skill knows a rule can have up
   to 5 targets — each target independently needs a DLQ ARN. Missing
   DLQ on ANY target is a silent data-loss vector for that target.

4. **AWS-owned vs customer-managed key distinction.** A generic assistant
   says "EventBridge is encrypted by default." The skill identifies that
   the default is an AWS-OWNED key (invisible in KMS console, no rotation
   control, no decrypt-audit) — a customer-managed key gives rotation
   control and CloudTrail data-event logging.

5. **Severity aggregation with per-finding breakdown.** The verdict is
   PUBLIC_BUS (worst finding), but the FINDINGS list shows individual
   severities: injection is PUBLIC_BUS, DLQ gap is NO_DLQ, encryption
   gap is NO_ENCRYPTION, archive gap is CONFIG_GAP, root statement is OK.

## Slash-command invocation

```
/aws:audit-eventbridge-bus-policy
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this event bridge bus before we go to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: eventbridge-bus-policy-auditor]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this event bridge bus policy"
# [Phase: Audit | Skills routed: eventbridge-bus-policy-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the bus posture:

```bash
# Verify the wildcard principal was removed
aws events describe-event-bus --name orders-bus-prod \
  --profile default --output json | jq '.Policy' | jq '.Statement[] | .Principal'

# Confirm DLQs are attached to all targets
aws events list-targets-by-rule --rule order-processing-rule \
  --event-bus-name orders-bus-prod --profile default | jq '.Targets[] | {Id, DeadLetterConfig}'

# Check archive status
aws events list-archives --name-prefix orders \
  --profile default --output json | jq '.Archives[] | {ArchiveName, State, RetentionDays}'
```

Then monitor CloudTrail for `events:PutEvents` from unexpected principals
for 1-2 weeks.
