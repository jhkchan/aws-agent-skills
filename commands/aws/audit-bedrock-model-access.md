---
description: Audit Amazon Bedrock model access posture — invocation logging coverage (S3/CloudWatch/DataFirehose), customer-managed KMS encryption, Anthropic Claude geo-block risk in APAC, provisioned throughput commitment state, and guardrail coverage.
nl_triggers:
  - "audit bedrock model access"
  - "check bedrock invocation logging"
  - "bedrock kms encryption"
  - "claude geo-block apac"
  - "bedrock provisioned throughput"
  - "bedrock guardrail coverage"
  - "bedrock inventory audit"
  - "bedrock logging configuration"
  - "is bedrock logging enabled"
  - "bedrock compliance posture"
  - "bedrock security audit"
routes_to: bedrock-model-access-inventory
---

# /aws:audit-bedrock-model-access

Activate the `bedrock-model-access-inventory` skill and audit a Bedrock
Model Access inventory for security and compliance posture.

## What it does

Reads a Bedrock inventory document (region, enabled models, invocation
logging config, KMS key, provisioned throughput, guardrails) and applies
ordered classification logic:

1. Invocation logging — no destinations or textDataDeliveryEnabled false
   is NO_LOGGING (forensic-trail loss).
2. KMS encryption — no customer-managed key is NO_ENCRYPTION (key-control
   loss, not confidentiality loss).
3. Geo-block risk — Anthropic Claude enabled in ap-* region is
   GEO_BLOCK_RISK (models listed but invocation-blocked).
4. Config gaps — single logging destination, expired provisioned
   throughput, missing guardrails, partial modality logging.
5. OK — multi-destination logging + CMK + no geo-block + no gaps.

Emits a deterministic VERDICT per inventory:

```text
INVENTORY: <account-id> / <region>
VERDICT: NO_LOGGING | NO_ENCRYPTION | GEO_BLOCK_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [NO_LOGGING] <finding description (Step N)>
  - [NO_ENCRYPTION] <secondary finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Bedrock inventory and ask any of:

- "audit our bedrock model access"
- "check bedrock invocation logging"
- "is bedrock KMS encrypted?"
- "will Claude work in our APAC region?"
- "are our bedrock guardrails configured?"
- "is bedrock logging enabled?"

A Bedrock inventory snapshot + any audit verb also routes here via the
orchestrator.

## Inputs

- A Bedrock Model Access inventory document containing:
  - Region and account ID
  - Enabled models (model IDs with provider)
  - Invocation logging configuration (s3Config, cloudwatchConfig,
    kinesisConfig, per-modality delivery flags)
  - KMS encryption (customer-managed key ARN or AWS-managed)
  - Provisioned throughput allocations (model, status, commitment end)
  - Guardrails (IDs and applied-model coverage)

## Outputs

- One VERDICT block per inventory (multiple findings aggregate to the
  worst by priority order).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: enable multi-destination logging, associate CMK,
  use Nova/gpt-oss for APAC, renew provisioned throughput, attach
  guardrails.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Bedrock AI/ML security).
- `/aws:audit-kms-key-policy` for auditing the KMS key used by Bedrock
  guardrails and knowledge bases.
