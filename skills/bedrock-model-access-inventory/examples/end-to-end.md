# End-to-end usage scenario: bedrock-model-access-inventory

A walkthrough showing the skill auditing a Bedrock account that has
invocation logging disabled (NO_LOGGING) combined with no customer-managed
KMS key, demonstrating the ordered classification priority, the
forensic-trail-loss concept, and the multi-destination remediation workflow.

## Input (user prompt)

> Audit our Bedrock model access posture before the SOC2 review next week.
> We have Claude and Nova enabled in us-east-1.

```
Bedrock Model Access Inventory:
Region: us-east-1
Account: 111111111111

Enabled models:
  - anthropic.claude-3-5-sonnet-20241022-v2:0 (Anthropic)
  - amazon.nova-pro-v1:0 (Amazon)

Invocation logging configuration:
  s3Config: (none)
  cloudwatchConfig: (none)
  kinesisConfig: (none)
  textDataDeliveryEnabled: false
  imageDataDeliveryEnabled: false
  embeddingDataDeliveryEnabled: false

KMS encryption:
  customerManagedKey: (none — AWS-managed)

Provisioned throughput: (none)

Guardrails: (none)
```

## Skill output

```text
INVENTORY: 111111111111 / us-east-1
VERDICT: NO_LOGGING
REASON: No invocation logging destinations configured — zero audit trail for
any model invocation across Claude and Nova (Step 1). No customer-managed KMS
key either (Step 2). The priority order is NO_LOGGING > NO_ENCRYPTION because
a forensic-trail loss is worse than a key-control loss.
FINDINGS:
  - [NO_LOGGING] s3Config, cloudwatchConfig, kinesisConfig all absent;
    textDataDeliveryEnabled is false (Step 1) — every prompt and response
    sent to enabled models is unlogged
  - [NO_ENCRYPTION] No customer-managed KMS key — AWS-managed only (Step 2) —
    no CloudTrail KMS events, no key-revocation capability
  - [CONFIG_GAP] No guardrails attached to enabled models (Step 4) — no
    content filtering or PII redaction
REMEDIATION:
  1. NO_LOGGING — Enable invocation logging with at least two destinations:
     aws bedrock put-invocation-logging --logging-config '{"s3Config":{"bucketName":"bedrock-invocation-logs","keyPrefix":"invocations/"},"cloudwatchConfig":{"logGroupName":"/aws/bedrock/invocations"},"textDataDeliveryEnabled":true,"imageDataDeliveryEnabled":true,"embeddingDataDeliveryEnabled":true}'
  2. NO_ENCRYPTION — Create a customer-managed KMS key and associate it with
     guardrails and the S3 log bucket:
     aws kms create-key --description "Bedrock encryption key"
  3. CONFIG_GAP — Create and attach guardrails:
     aws bedrock create-guardrail --name default-guardrail ...
  4. Back up before changes — put-invocation-logging REPLACES the config:
     aws bedrock get-invocation-logging > /tmp/bedrock-logging-backup.json
```

## What the skill caught that a generic assistant misses

1. **The forensic-trail-loss concept.** A generic assistant says "you should
   enable logging." The skill explains that without invocation logging, there
   is ZERO audit trail for any model invocation — no record of which prompts
   were sent, what data was included, or what responses were generated. For a
   SOC2 review, this is a blocking finding.

2. **The priority order matters.** The verdict is NO_LOGGING, not
   NO_ENCRYPTION, even though both findings exist. The skill explains why:
   a forensic-trail loss (no logging) is worse than a key-control loss (no
   CMK), because AWS-managed encryption still protects data at rest, while
   absent logging means irrecoverable loss of audit evidence.

3. **The `textDataDeliveryEnabled` trap.** Even if logging destinations
   existed, the `textDataDeliveryEnabled: false` flag would still produce
   NO_LOGGING. The skill catches that text is the primary LLM modality —
   destinations without text delivery are cosmetic.

4. **The `put-invocation-logging` REPLACES warning.** Generic advice says
   "enable logging." The skill warns that `put-invocation-logging` overwrites
   the entire config — no merge, no version history, no rollback. Always back
   up first.

## Slash-command invocation

```
/aws:audit-bedrock-model-access
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our bedrock model access before the SOC2 review"
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the posture:

```bash
# Verify invocation logging is active
aws bedrock get-invocation-logging --profile default

# List enabled models and their providers
aws bedrock list-foundation-models --profile default --region us-east-1 \
  --by-inference-type ON_DEMAND

# Check for expired provisioned throughput
aws bedrock list-provisioned-model-throughputs --profile default

# Verify guardrails exist
aws bedrock list-guardrails --profile default
```

Then monitor CloudWatch for invocation-volume spikes over the next 1-2 weeks
to confirm the logging pipeline is capturing events.
