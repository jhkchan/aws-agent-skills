---
name: bedrock-model-access-inventory
description: >-
  Audits Amazon Bedrock model access posture — invocation logging coverage
  (S3/CloudWatch/DataFirehose destinations and per-modality delivery flags),
  customer-managed KMS encryption versus AWS-managed default, Anthropic
  Claude geo-block risk in APAC jurisdictions (models list as enabled but
  fail at invocation with ValidationException), provisioned throughput
  commitment state, and guardrail coverage on enabled models. Emits a
  deterministic verdict (NO_LOGGING | NO_ENCRYPTION | GEO_BLOCK_RISK |
  CONFIG_GAP | OK) per Bedrock account inventory. Use when reviewing
  Bedrock model access, checking invocation logging, validating KMS
  encryption, assessing Claude geo-block exposure, or auditing provisioned
  throughput commitments.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline inventory-document classification.
  Live-account audits use aws bedrock get-invocation-logging, aws bedrock
  list-foundation-models, aws bedrock list-provisioned-model-throughputs,
  and aws bedrock list-guardrails (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Bedrock
  - model access
  - invocation logging
  - KMS encryption
  - geo-block
  - Claude APAC
  - provisioned throughput
  - guardrails
  - Nova
  - DataFirehose
  - audit trail
  - compliance
  - model inventory
tags: [bedrock, ai-ml, security, invocation-logging, kms-encryption, geo-block, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  verdict_shape: "NO_LOGGING | NO_ENCRYPTION | GEO_BLOCK_RISK | CONFIG_GAP | OK | ERROR"
  when_to_use: >-
    Reviewing Bedrock model access before production deployment, auditing
    invocation logging coverage, validating customer-managed KMS encryption,
    assessing Anthropic Claude geo-block risk in APAC, checking provisioned
    throughput commitment state, or hardening Bedrock security posture.
  activation_triggers:
    - "audit bedrock model access"
    - "check bedrock invocation logging"
    - "is bedrock kms encrypted"
    - "claude geo-block apac"
    - "bedrock provisioned throughput"
    - "bedrock guardrail coverage"
    - "bedrock inventory audit"
  invocation_schema: >-
    Input: a Bedrock Model Access inventory document (region, enabled models,
    invocation logging config, KMS key, provisioned throughput, guardrails).
    Output: deterministic INVENTORY/VERDICT/REASON/FINDINGS/REMEDIATION block
    where VERDICT is one of {NO_LOGGING, NO_ENCRYPTION, GEO_BLOCK_RISK,
    CONFIG_GAP, OK}.
---

# Bedrock Model Access Inventory Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** finding in a fixed
priority order — logging before encryption before geo-block before
config-gap — because a forensic-trail loss (no logging) is worse than a
key-control loss (no CMK), which is worse than an availability
false-positive (geo-blocked Claude), which is worse than a minor config
issue (expired provisioned throughput).

Bedrock model access is the gate between your data and foundation models.
Three dimensions define its security posture:

- **Invocation logging** is the **forensic spine**. Without it, there is no
  audit trail of which prompts were sent to which models, what data was
  included, or what responses were generated. A Bedrock account with models
  enabled but no invocation logging has zero breach-investigation capability.
- **Customer-managed KMS** is the **key-control layer**. AWS-managed
  encryption still encrypts at rest, but you cannot audit key-usage events
  in CloudTrail, cannot revoke access during an incident, and cannot apply
  key-level IAM policies. The gap is control, not confidentiality.
- **Geo-block risk** is an **availability false-positive**. Anthropic Claude
  models appear in `list-foundation-models` and can be enabled in Model
  Access, but `converse`/`invoke-model` returns `ValidationException` in
  APAC jurisdictions. The listing is misleading — the model is listed but
  blocked at invocation, not at enablement.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| All logging destinations absent (S3/CW/Firehose) | **NO_LOGGING** | 1 |
| Destinations present but `textDataDeliveryEnabled: false` | **NO_LOGGING** | 1 |
| Destinations present but all modality flags false | **NO_LOGGING** | 1 |
| Logging active (text delivery on); no customer-managed KMS key | **NO_ENCRYPTION** | 2 |
| CMK present; Anthropic models enabled in `ap-*` region | **GEO_BLOCK_RISK** | 3 |
| CMK present; single logging destination only | **CONFIG_GAP** | 4 |
| CMK present; provisioned throughput commitment expired | **CONFIG_GAP** | 4 |
| CMK present; enabled models without guardrails | **CONFIG_GAP** | 4 |
| CMK present; image/embedding delivery disabled | **CONFIG_GAP** | 4 |
| Multi-destination logging + CMK + no geo-block + no gaps | **OK** | 5 |

Priority order (first match wins): `NO_LOGGING > NO_ENCRYPTION >
GEO_BLOCK_RISK > CONFIG_GAP > OK`.

## Pre-flight: input validation

If the inventory document is malformed (missing required sections,
unparseable), output:

```text
INVENTORY: <account/region or "unknown">
VERDICT: ERROR
REASON: Bedrock inventory document is malformed — cannot classify.
REMEDIATION: Re-fetch with aws bedrock get-invocation-logging and aws bedrock list-foundation-models.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious Bedrock behaviors

Each behavior changes the verdict if ignored:

- **Invocation logging is account-level, not per-model.** Once enabled via
  `put-invocation-logging`, it captures ALL model invocations across the
  account. There is no API to log only specific models. If logging is off,
  every model is unlogged; if on, every model is logged.

- **`textDataDeliveryEnabled` is the critical modality flag.** Text is the
  primary data type for LLM invocations (prompt + response). Even if S3 and
  CloudWatch destinations are configured, if `textDataDeliveryEnabled` is
  false, text prompts are NOT captured. The configuration LOOKS enabled but
  silently misses the most common modality. Treat as NO_LOGGING, not
  CONFIG_GAP.

- **Claude geo-block fires at invocation, not at enablement.** Anthropic
  models appear in `list-foundation-models` in APAC regions (ap-southeast,
  ap-northeast, ap-south, ap-east) and can be subscribed in Model Access.
  But `converse` / `invoke-model` returns `ValidationException`. The block
  is jurisdictional (APAC), not account-specific. Amazon Nova, Titan,
  gpt-oss, Mistral, and Meta Llama models are NOT blocked. Do NOT classify
  Claude as "enabled and functional" in APAC — it is enabled but
  invocation-blocked.

- **Provisioned throughput commitment is time-bounded.** A PT allocation
  has `status: active` during the commitment term and transitions to
  `expired` after the commitment end date. After expiry, the model falls
  back to on-demand billing at a higher per-token rate. An expired PT is a
  cost/config gap, not a security risk.

- **KMS for Bedrock applies to guardrails, knowledge bases, and log
  delivery — not model invocations.** Model prompts/responses in transit
  use TLS; at rest within Bedrock infrastructure, data is encrypted with
  AWS-managed keys (not customer-controllable). A customer-managed KMS key
  applies to: guardrail storage (`create-guardrail --kms-key-id`),
  knowledge-base vector-store encryption, and S3 bucket encryption for
  invocation log delivery. The NO_ENCRYPTION finding means you lack
  key-control over these artifacts, not that invocations are unencrypted.

- **DataFirehose delivery has a buffering delay (60-900 seconds).** When
  using Kinesis Data Firehose as a logging destination, logs are buffered
  before delivery to S3. For real-time alerting, CloudWatch Logs is the
  correct destination; Firehose is for batch/archival. A config with only
  Firehose (no CloudWatch) lacks real-time monitoring capability.

- **Cross-region inference profiles log the profile ARN, not the backing
  region.** When using a profile (e.g., `us.anthropic.claude-...`), the
  invocation log records the profile, not the specific region that
  processed the request. This matters for data-residency compliance: you
  cannot prove which region saw the prompt from logs alone.

- **Guardrails are evaluated at invocation, not at enablement.** A model
  can be enabled without any guardrail attached. Guardrails are applied
  per-invocation (via `guardrailIdentifier` in the converse call) or
  per-inference-profile. The absence of guardrails on enabled models means
  no content filtering, no PII redaction, and no topic denial — a data-
  protection gap even when logging and encryption are healthy.

- **`put-invocation-logging` is a REPLACE, not a merge.** Calling it
  overwrites the entire logging configuration. Always capture the current
  config with `get-invocation-logging` before any modification — there is
  no version history and no rollback.

- **S3 bucket policy is REQUIRED for log delivery — `put-invocation-logging`
  succeeds silently without it.** The S3 bucket receiving invocation logs
  MUST have a bucket policy granting `s3:PutObject` to the Bedrock service
  principal (`logging.bedrock.amazonaws.com` or `bedrock.amazonaws.com`
  depending on region). Without this policy, the API call returns success
  but NO logs are ever delivered — a silent failure that looks healthy in
  the console. This is the most common logging-misconfiguration trap: the
  logging config appears enabled, but the bucket rejects writes.

- **CloudWatch Logs resource policy is REQUIRED for CW delivery.** Similarly,
  the CloudWatch log group must have a resource policy allowing
  `bedrock.amazonaws.com` to create log streams and put log events. Without
  it, Bedrock cannot write invocation logs to CloudWatch, even though the
  logging config names the log group. Verify with
  `aws logs describe-resource-policies` and check for a policy that includes
  `logs:CreateLogStream` and `logs:PutLogEvents` for the Bedrock principal.

- **CMK key rotation for the Bedrock-associated key matters.** The
  customer-managed KMS key used for guardrail encryption and knowledge-base
  vector stores should have `EnableKeyRotation: true`. A CMK with rotation
  disabled on a symmetric key is an additive CONFIG_GAP finding (same
  principle as KMS key auditing: unbounded exposure window if key material
  is compromised). Verify with
  `aws kms get-key-rotation-status --key-id <bedrock-key-id>`.

- **`bedrock:PutInvocationLogging` requires service-level IAM permission.**
  The principal enabling logging needs `bedrock:PutInvocationLogging` in
  their identity-based policy — this is NOT a resource-level permission and
  cannot be scoped via a resource ARN. A role with only
  `bedrock:ListFoundationModels` will fail to enable logging with
  `AccessDeniedException`. Verify the auditor role's permissions before
  attempting remediation.

- **Invocation logs contain the FULL prompt and response text — the log
  destination itself becomes a sensitive-data store.** Bedrock invocation
  logging captures complete input prompts and model outputs verbatim,
  including any PII, credentials, API keys, or proprietary data the
  application sent to the model. The S3 bucket and CloudWatch log group
  receiving these logs must have TIGHTER access controls than a typical
  log bucket — a broad bucket policy or permissive log-group IAM grant
  effectively re-exposes every sensitive payload the model ever processed.
  Treat the logging destinations as Tier-1 sensitive-data stores with
  their own access-review cadence.

- **Knowledge-base data ingestion is NOT covered by invocation logging.**
  When a Bedrock knowledge base ingests source documents
  (`bedrock:IngestKnowledgeBaseDocuments` or automated sync), the document
  content flows into the vector store and is NOT captured in invocation
  logs. Only the downstream model invocation (converse/invoke) that reads
  the vector store is logged — the ingestion step is invisible. This means
  sensitive data can enter the RAG pipeline without any log trail. A
  compliance audit that checks invocation logs alone misses the data-
  ingestion path entirely.

- **Cross-region inference profiles record logs in the profile's home
  region, not the caller's region.** When an invocation is routed via a
  cross-region profile (e.g., `us.anthropic.claude-3-5-sonnet-...`), the
  invocation log is emitted in the region where the profile is managed,
  not the region of the calling account. A logging config verified in
  us-east-1 may silently miss invocations that were routed to us-west-2
  via the profile. To ensure full coverage, verify logging configuration
  in every region where a cross-region inference profile is active.

- **Guardrail evaluations are recorded inside the invocation log entry,
  not as separate events.** When a guardrail blocks or redacts content,
  the action is embedded in the invocation log record under
  `guardrail` fields (interventions, masked output). This signal is often
  overlooked because it is nested deep in the log payload. A monitoring
  pipeline that ignores the guardrail sub-objects misses the only
  programmatic evidence that content filtering fired.

### Step 1: Invocation logging evaluation (highest priority)

Check the invocation logging configuration:

1. **All destinations absent.** If `s3Config`, `cloudwatchConfig`, and
   `kinesisConfig` are all `(none)` / absent / null → **NO_LOGGING**.

2. **Text delivery disabled.** If destinations are configured but
   `textDataDeliveryEnabled` is `false` → **NO_LOGGING**. Text is the
   primary LLM modality; logging without text capture is cosmetic.

3. **All modalities disabled.** If `textDataDeliveryEnabled`,
   `imageDataDeliveryEnabled`, and `embeddingDataDeliveryEnabled` are all
   false (regardless of destinations configured) → **NO_LOGGING**.

4. **At least one destination + text delivery enabled.** Logging is
   ACTIVE. Proceed to Step 2. Record secondary gaps (single destination,
   missing modalities) for Step 4.

### Step 2: KMS encryption evaluation

- **No CMK** (`customerManagedKey: (none — AWS-managed)`) →
  **NO_ENCRYPTION**. The account relies solely on AWS-managed encryption.
  While data IS encrypted at rest, the account cannot audit KMS key-usage
  events in CloudTrail, cannot revoke access during an incident, and cannot
  apply key-level IAM policies for granular access control.

- **CMK present** (`customerManagedKey: <key-arn>`) → OK for this
  dimension. Proceed to Step 3.

### Step 3: Geo-block risk evaluation

- **Region starts with `ap-` AND any Anthropic model is enabled** →
  **GEO_BLOCK_RISK**. The Claude models are listed and enabled but will
  fail at invocation with `ValidationException`. This is a jurisdictional
  block, not an account-specific issue.

- **Region does NOT start with `ap-` OR no Anthropic models enabled** →
  no geo-block risk. Proceed to Step 4.

- **Nova, Titan, gpt-oss, Mistral, Meta Llama** are NOT geo-blocked in
  any region. Only Anthropic Claude models carry the APAC geo-block.

### Step 4: Config-gap evaluation

If logging is active (Step 1 passed), CMK is present (Step 2 passed), and
no geo-block risk (Step 3 passed), evaluate secondary gaps:

- **Single logging destination.** Only one of {S3, CloudWatch, Firehose}
  configured. No redundancy — if that destination fails (bucket deleted,
  log group removed, stream error), invocations are silently unlogged.
  → **CONFIG_GAP**

- **Provisioned throughput commitment expired.** Any PT allocation with
  `status: expired`. The model falls back to on-demand billing at higher
  per-token cost. → **CONFIG_GAP**

- **Enabled models without guardrails.** Models are enabled but the
  guardrails section is `(none)` or does not cover all enabled models.
  No content filtering or PII redaction. → **CONFIG_GAP**

- **Partial modality logging.** `imageDataDeliveryEnabled` or
  `embeddingDataDeliveryEnabled` is `false` while image/embedding models
  are enabled. → **CONFIG_GAP**

If none apply → proceed to Step 5.

### Step 5: OK

If no step produces a finding → **OK**. The inventory has multi-destination
logging, a customer-managed KMS key, no APAC geo-block risk, and no
secondary config gaps.

## Output format (per inventory)

```text
INVENTORY: <account-id> / <region>
VERDICT: NO_LOGGING | NO_ENCRYPTION | GEO_BLOCK_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [NO_LOGGING] <finding description (Step N)>
  - [NO_ENCRYPTION] <secondary finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — no invocation logging

```text
INVENTORY: 111111111111 / us-east-1
VERDICT: NO_LOGGING
REASON: No invocation logging destinations configured — zero audit trail for
any model invocation (Step 1). No customer-managed KMS key either (Step 2).
FINDINGS:
  - [NO_LOGGING] s3Config, cloudwatchConfig, kinesisConfig all absent (Step 1)
  - [NO_ENCRYPTION] No customer-managed KMS key — AWS-managed only (Step 2)
REMEDIATION:
  1. Enable invocation logging with at least two destinations:
     aws bedrock put-invocation-logging --logging-config '{"s3Config":{"bucketName":"bedrock-invocation-logs","keyPrefix":"invocations/"},"cloudwatchConfig":{"logGroupName":"/aws/bedrock/invocations"},"textDataDeliveryEnabled":true,"imageDataDeliveryEnabled":true}'
  2. Associate a customer-managed KMS key for guardrail and log-delivery encryption.
```

## Anti-Patterns — NEVER

- NEVER classify a logging configuration with `textDataDeliveryEnabled:
  false` as anything other than NO_LOGGING. Text is the primary LLM
  modality. Destinations configured without text delivery are receiving
  nothing useful — the logging is cosmetic, not functional.

- NEVER assume Anthropic Claude models are invocable in APAC regions just
  because they appear in `list-foundation-models`. The listing shows
  
  at the API layer in APAC jurisdictions. Always check the region prefix.

- NEVER treat AWS-managed encryption as equivalent to customer-managed KMS
  for compliance. AWS-managed keys encrypt at rest, but the account cannot
  demonstrate key-usage auditability (no CloudTrail KMS events), cannot
  revoke access during an incident, and cannot apply granular key policies.
  Compliance frameworks (SOC2, HIPAA, GDPR) require customer-managed key
  control for sensitive data.

- NEVER flag a single-destination logging configuration as NO_LOGGING. A
  single destination (e.g., S3 only) with text delivery enabled IS logging.
  The single destination is a redundancy gap (CONFIG_GAP), not a logging
  absence. Downgrading to NO_LOGGING causes alert fatigue.

- NEVER classify Nova, Titan, gpt-oss, Mistral, or Meta Llama models as
  GEO_BLOCK_RISK. Only Anthropic Claude models carry the APAC invocation
  geo-block. Non-Anthropic models are available in all supported regions.

- NEVER ignore expired provisioned throughput commitments. An expired PT
  silently transitions the model to on-demand billing — often 2-3x more
  expensive per token. This is a cost leak, not a security risk, but it is
  a legitimate CONFIG_GAP finding.

- NEVER assume guardrails are automatically attached to enabled models.
  Guardrails are applied per-invocation or per-inference-profile. An
  enabled model without guardrails has no content filtering, no PII
  redaction, and no topic denial — a data-protection gap even when logging
  and encryption are healthy.

- NEVER conflate DataFirehose with CloudWatch Logs for real-time
  monitoring. Firehose buffers for 60-900 seconds before delivering to S3.
  CloudWatch Logs is near-real-time. A config with only Firehose lacks
  real-time alerting capability — flag as CONFIG_GAP.

- NEVER treat cross-region inference profiles as a reliable geo-block
  workaround. A profile like `us.anthropic.claude-3-5-sonnet-...` routes
  across US regions, but if the calling account is in APAC, the base
  model's jurisdictional check may still apply. Verify by testing an
  actual invocation, not by assuming the profile bypasses the block.

- NEVER call `put-invocation-logging` without first capturing the current
  configuration. The call REPLACES the entire logging config — there is no
  merge, no version history, and no rollback. Always back up with
  `get-invocation-logging` before any modification.

- NEVER assume invocation logs are being delivered just because
  `put-invocation-logging` returned success. The S3 bucket must have a
  policy granting `s3:PutObject` to the Bedrock service principal, and the
  CloudWatch log group must have a resource policy allowing
  `bedrock.amazonaws.com` to write. Verify actual log delivery by checking
  for recent objects/events after enabling — a missing bucket policy is a
  silent failure that looks healthy in the console.

- NEVER point invocation logging at an S3 bucket without a lifecycle policy.
  Invocation logs accumulate indefinitely — a high-traffic Bedrock account
  can generate gigabytes per day. Without a lifecycle rule (transition to
  Glacier after 90 days, expire after 365 days), the bucket grows unbounded,
  creating a cost and operability risk that undermines the logging investment.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before enabling/modifying invocation
  logging or associating a KMS key, emit:
  `CONFIRM: About to modify Bedrock invocation logging for account
  <account> in region <region>. This affects audit-trail capture for all
  model invocations. Proceed? (yes/no)`

- **Logging enablement is destructive.** `put-invocation-logging` REPLACES
  the entire configuration. Always capture the current config:
  `aws bedrock get-invocation-logging --profile <p> >
  /tmp/bedrock-logging-backup-$(date +%s).json`

- **S3 bucket lifecycle.** Invocation logs accumulate indefinitely. Before
  pointing logging at an S3 bucket, verify a lifecycle policy exists to
  transition/archive old logs.

- **KMS key policy check.** Before associating a CMK, verify the key policy
  permits `bedrock.<region>.amazonaws.com` to use it. A CMK that blocks
  the Bedrock service principal silently breaks guardrail creation.

- **Guardrail attachment is not retroactive.** Existing application code
  must be updated to pass `guardrailIdentifier` in the converse call.

## Remediation guidance

### For NO_LOGGING

1. Enable invocation logging with at least two destinations and all
   modalities:
   ```bash
   aws bedrock put-invocation-logging \
     --logging-config '{"s3Config":{"bucketName":"bedrock-invocation-logs","keyPrefix":"invocations/"},"cloudwatchConfig":{"logGroupName":"/aws/bedrock/invocations"},"textDataDeliveryEnabled":true,"imageDataDeliveryEnabled":true,"embeddingDataDeliveryEnabled":true}' \
     --profile <p> --region <r>
   ```
2. Verify: `aws bedrock get-invocation-logging --profile <p>`
3. Set an S3 lifecycle policy on the log bucket (Glacier after 90 days,
   expire after 365 days).
4. Create a CloudWatch metric filter on the log group for high-token
   invocations (cost anomaly detection).

### For NO_ENCRYPTION

1. Create or identify a customer-managed KMS key:
   `aws kms create-key --description "Bedrock encryption key" --profile <p>`
2. Add a key policy allowing Bedrock to use it, then create an alias:
   `aws kms create-alias --alias-name alias/bedrock-encryption --target-key-id <key-id>`
3. Re-create guardrails with the CMK:
   `aws bedrock create-guardrail --name secured-guardrail --kms-key-id <key-id> ...`
4. Enable SSE-KMS on the S3 bucket receiving invocation logs.

### For GEO_BLOCK_RISK

1. If Claude is required and the account is in APAC:
   - Use Amazon Nova Pro/Lite as the primary model (not geo-blocked).
   - Use gpt-oss models as an alternative (not geo-blocked).
   - If Claude is strictly required, invoke from a non-APAC region
     (us-east-1, eu-west-1) via a cross-region inference profile.
2. Test an actual invocation to confirm the block:
   ```bash
   aws bedrock-runtime converse --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
     --messages '[{"role":"user","content":[{"text":"test"}]}]' \
     --profile <p> --region ap-southeast-1
   # Expect: ValidationException if geo-blocked
   ```
3. Remove Claude models from the enabled list if they cannot be invoked,
   to prevent application-level confusion.

### For CONFIG_GAP

1. **Single destination:** add a second logging destination (CloudWatch
   for real-time + S3 for archival).
2. **Expired PT:** renew the commitment or transition to on-demand with a
   cost-monitoring budget.
3. **No guardrails:** create and attach guardrails to enabled models:
   `aws bedrock create-guardrail --name default-guardrail ...`
4. **Partial modality:** enable image/embedding delivery if those model
   types are in use.

### For OK

1. No remediation required.
2. Recommend periodic review of enabled models (remove unused).
3. Recommend CloudWatch alarms on invocation-volume spikes.
4. Recommend quarterly review of provisioned throughput commitments.

## Recent AWS features (2024-2026)

- **Cross-region inference profiles (2024-2025):** Bedrock now supports cross-region inference profiles that route requests across regions for higher throughput. Auditors must account for inference profiles in the model-access inventory — a model may appear accessible but its inference profile may not be enabled, or vice versa.
- **Bedrock marketplace models (2024):** Third-party models (e.g., Llama, Mistral) are now available via Bedrock Marketplace. These models have different access-request flows than first-party models. Auditors should inventory marketplace models separately and verify their invocation logging coverage.
- **Provisioned throughput with inference profiles:** Provisioned throughput commitments now interact with cross-region inference profiles. Auditors should verify that provisioned throughput units (PTUs) are not over-committed or under-utilized, and that model unit (MU) quotas are tracked.
- **Model distillation and evaluation jobs (2024-2025):** Bedrock Distillation and Evaluation Jobs are new capabilities that create additional invocation surfaces. Auditors should verify these jobs are covered by invocation logging and guardrails.
- **New model families (2024-2026):** Amazon Nova models (Micro/Lite/Pro/Premier), Claude 3.5/4 (Sonnet/Haiku/Opus), Llama 3/4, and DeepSeek models expand the model-access inventory surface. Each new model requires its own access-request and IAM evaluation.

## Domain

AWS CloudOps / Bedrock AI-ML Security & Compliance.
