---
name: sqs-dlq-policy-auditor
description: >-
  Audits AWS SQS queues for dead-letter-queue (DLQ) configuration gaps, public
  access via Principal:* queue policies, encryption-at-rest status (SSE-SQS /
  SSE-KMS), maxReceiveCount tuning, message-retention periods, and cross-account
  DLQ accessibility. Emits a deterministic verdict (NO_DLQ | PUBLIC_ACCESS |
  NO_ENCRYPTION | CONFIG_GAP | OK) per queue with enumerated findings and
  specific CLI remediation. Use when reviewing SQS queue configurations,
  checking for missing or misconfigured dead-letter queues, validating
  encryption posture, auditing queue policies for public exposure, or tuning
  redrive-policy parameters before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline attribute-document classification.
  Live-account audits use aws sqs get-queue-attributes, aws sqs list-queues,
  and aws sqs get-queue-url (AWS CLI v2, SSO or key-based credentials).
keywords:
  - SQS
  - dead-letter queue
  - DLQ
  - redrive policy
  - maxReceiveCount
  - queue policy
  - Principal:"*"
  - public access
  - SSE-SQS
  - SSE-KMS
  - KmsMasterKeyId
  - SqsManagedSseEnabled
  - message retention
  - cross-account DLQ
  - FIFO queue
  - poison pill
  - RedriveAllowPolicy
  - VisibilityTimeout
  - SQS audit
  - queue security
tags: [sqs, app-integration, dead-letter-queue, redrive-policy, encryption, queue-policy, public-access, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  verdict_shape: "NO_DLQ | PUBLIC_ACCESS | NO_ENCRYPTION | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an SQS queue configuration before production deployment, checking
    for a missing dead-letter queue, auditing a queue policy for public access,
    validating encryption-at-rest, tuning maxReceiveCount, inspecting DLQ
    retention, or hardening SQS posture across an account.
  activation_triggers:
    - "audit this SQS queue"
    - "is my SQS queue missing a DLQ"
    - "check SQS redrive policy"
    - "is my SQS queue public"
    - "SQS queue encryption"
    - "maxReceiveCount tuning"
    - "DLQ retention period"
    - "cross-account DLQ"
    - "poison pill SQS"
    - "harden SQS queue"
  invocation_schema: >-
    Input: either (a) an SQS queue attribute document (Policy, RedrivePolicy,
    KmsMasterKeyId, SqsManagedSseEnabled, MessageRetentionPeriod,
    VisibilityTimeout), optionally paired with DLQ attributes, OR (b) a queue
    URL/ARN for live-account audit. Output: deterministic QUEUE/VERDICT/REASON/
    FINDINGS/REMEDIATION block per queue, where VERDICT is one of NO_DLQ,
    PUBLIC_ACCESS, NO_ENCRYPTION, CONFIG_GAP, OK.
---

# SQS DLQ Policy Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
five dimensions, and three SQS behaviours catch even experienced engineers —
`Principal: "*"` in a queue policy is usually **safe** (S3/SNS notification
pattern), `maxReceiveCount` counts **per delivery not per consumer**, and
`RedrivePolicy` is a **JSON-encoded string** that must be parsed before
classification.

A dead-letter queue is the only safety net against poison-pill messages. A
queue without a DLQ silently retries bad messages until they expire, burning
through compute budget and starving healthy messages. Public queue policies
expose message payloads to any AWS account. Missing encryption leaves message
bodies in plaintext at rest.

## Quick reference — verdict thresholds

| Condition | Verdict | Risk | Rule |
|---|---|---|---|
| `Principal: "*"` + `sqs:SendMessage`/`sqs:*`/`*` + no strong condition | **PUBLIC_ACCESS** | CRITICAL | Step 1 |
| No `RedrivePolicy` attribute / missing `deadLetterTargetArn` | **NO_DLQ** | HIGH | Step 2 |
| Neither `SqsManagedSseEnabled: true` nor `KmsMasterKeyId` set | **NO_ENCRYPTION** | HIGH | Step 3 |
| `maxReceiveCount` <= 1 (too aggressive) | **CONFIG_GAP** | MEDIUM | Step 4a |
| `maxReceiveCount` > 1000 (poison-pill loop) | **CONFIG_GAP** | MEDIUM | Step 4b |
| DLQ `MessageRetentionPeriod` < 345600 (4 days) | **CONFIG_GAP** | MEDIUM | Step 4c |
| DLQ ARN in a different account + no `RedriveAllowPolicy` granting access | **CONFIG_GAP** | MEDIUM | Step 4d |
| All dimensions pass | **OK** | LOW | Step 5 |

See the ordered steps below for edge cases (Principal:"*" with SourceArn,
FIFO DLQ constraints, VisibilityTimeout interaction).

## Pre-flight: queue metadata gate

Before evaluating the queue policy and redrive configuration, classify the
queue itself. Several attributes short-circuit or modify the audit.

**Multi-queue / account-wide sweep note (pagination):** `aws sqs list-queues`
returns up to 1000 queue URLs per page. Use `--next-token` (from the prior
`NextToken`) to page through all queues; iterating only the first page
silently misses queues. For each URL, `aws sqs get-queue-attributes
--queue-url <url> --attribute-names All` returns all attributes in one call
(no pagination needed for attributes).

| Attribute | Value | Effect on audit |
|---|---|---|
| `FifoQueue` | `true` | **FIFO queue.** DLQ must also be FIFO. maxReceiveCount tuning is MORE critical — a poison pill in a message group blocks the entire group until moved to DLQ. |
| `FifoQueue` | `false` / absent | **Standard queue.** Normal audit. |
| `ContentBasedDeduplication` | `true` (FIFO) | Deduplication runs before receive count — a retried message with the same dedup ID does NOT increment the counter. Poison pills persist longer than expected. |
| `Policy` | absent / empty | **No resource-based policy.** Only IAM identity-based policies govern access. This is the SECURE default — do not flag as a gap. |
| `KmsMasterKeyId` | set | **SSE-KMS encryption.** Customer-managed or AWS-managed KMS key. Encryption is satisfied. |
| `SqsManagedSseEnabled` | `true` | **SSE-SQS encryption.** Amazon SQS-managed encryption (free, FIPS-compliant). Encryption is satisfied. |

**If the queue attribute document is malformed** (the `Policy` field is not
valid JSON, or `RedrivePolicy` is not valid JSON when present), output:

```text
QUEUE: <queue-url>
VERDICT: ERROR
REASON: Queue attribute document is malformed — <field> is not valid JSON.
REMEDIATION: Re-fetch with `aws sqs get-queue-attributes --queue-url <url> --attribute-names All --output json` and re-audit.
```

**RedrivePolicy is a JSON-encoded string, not a native attribute.**
`aws sqs get-queue-attributes` returns `RedrivePolicy` as a
JSON-encoded **string** (double-encoded in the CLI JSON output). You MUST
parse the inner JSON before reading `deadLetterTargetArn` and
`maxReceiveCount`. A classification that reads the raw string as a dict
produces false NO_DLQ verdicts — the field looks absent because it was never
parsed.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious SQS behaviours that change classification

These behaviours are easy to misjudge without operational SQS experience.
Each changes a verdict if ignored:

- **`Principal: "*"` in an SQS queue policy is COMMON and usually SAFE.** The
  standard S3-event-notification and SNS-subscription patterns use
  `Principal: "*" + Condition: aws:SourceArn` (or `aws:SourceAccount`). The
  condition restricts access to the specific S3 bucket or SNS topic — it is
  real access control. Do NOT flag these as PUBLIC_ACCESS. Only flag
  `Principal: "*"` with NO strong condition (Step 1).

- **`maxReceiveCount` counts per message delivery, not per consumer.** Every
  `ReceiveMessage` call that delivers a message increments the counter —
  regardless of which consumer received it. With 10 consumers polling, a
  `maxReceiveCount` of 5 means roughly 0.5 effective retries per consumer
  before the message hits the DLQ. High-consumer queues need a HIGHER
  maxReceiveCount to survive consumer contention.

- **FIFO poison pills block the entire message group.** On a FIFO queue, a
  message that fails processing stays at the head of its message group.
  Messages behind it are not delivered until it is removed (consumed or moved
  to DLQ). A `maxReceiveCount` of 100 on a FIFO queue means up to 100 retry
  cycles where the ENTIRE message group is stalled. DLQ tuning is MORE
  critical for FIFO queues than for standard queues.

- **SSE-SQS (`SqsManagedSseEnabled`) is free and FIPS-validated.** It uses
  AWS-managed key material (rotation handled by SQS, 256-bit AES-GCM). For
  most compliance frameworks (SOC2, PCI-DSS, HIPAA), SSE-SQS satisfies
  at-rest encryption requirements. SSE-KMS (`KmsMasterKeyId`) adds
  customer-managed key control, CloudTrail decrypt logging, and per-API KMS
  cost (~$0.03 per 10k requests). Do NOT flag a queue with SSE-SQS as
  unencrypted — only flag when NEITHER is enabled.

- **`RedriveAllowPolicy` controls who can use a queue as a DLQ.** A DLQ with
  `redrivePermission: "allowAll"` accepts redriven messages from ANY queue
  in the same account. This is a blast-radius concern: a misconfigured
  source queue can flood a shared DLQ, drowning legitimate failed messages.
  `redrivePermission: "byQueue"` with explicit source-queue ARNs is the
  least-privilege pattern.

- **DLQ cross-region is silently rejected at configuration time.** The SQS
  `SetQueueAttributes` API rejects a `RedrivePolicy` whose
  `deadLetterTargetArn` is in a different region. However, if the policy was
  set via CloudFormation drift or a stale config snapshot, the ARN may
  appear in the attribute document without being effective. Always verify
  the DLQ ARN region matches the source queue region.

- **`VisibilityTimeout` x `maxReceiveCount` = effective retry window.** A
  VisibilityTimeout of 30s with maxReceiveCount of 5 gives an effective
  retry window of ~150 seconds before the message hits the DLQ. If the
  consumer's p99 processing time exceeds VisibilityTimeout, the message
  returns to the queue before processing completes, and the receive count
  increments — even though the consumer did not fail. This is the #1 cause
  of false-positive DLQ entries.

- **Lambda event source mapping interaction.** When Lambda consumes SQS, the
  event source mapping calls `DeleteMessage` on successful invocation. If
  the function throws, the message returns after the batch window expires.
  The Lambda service's `MaxBatchingWindowInSeconds` adds delay between
  retries. A `maxReceiveCount` of 3 with Lambda means only ~3 Lambda
  invocations before DLQ — often too few for transient downstream failures.

- **`aws sqs start-message-move-task`** (the current redrive API) moves
  messages from DLQ back to a source queue. It replaced the legacy
  `Redrive` API (deprecated 2022). The task is asynchronous and rate-limited
  — large DLQs take minutes to drain. Do NOT recommend the legacy API.

- **Batch `ReceiveMessage` increments ALL messages' counts.** When using
  `MaxNumberOfMessages > 1`, every message in the batch has its receive
  count incremented at delivery time. If the consumer processes 9 of 10
  successfully but throws on the 10th, all 10 are closer to the DLQ (the 9
  will be deleted on success, but their count was already incremented).

- **Attribute names are case-sensitive.** `aws sqs get-queue-attributes`
  returns `RedrivePolicy`, `KmsMasterKeyId`, `SqsManagedSseEnabled`,
  `MessageRetentionPeriod`, `VisibilityTimeout`, `Policy` — all
  PascalCase. Requesting `redrivePolicy` (lowercase) silently returns
  nothing. When parsing raw API output, match the exact casing.

### Step 1: Public access via queue policy (PUBLIC_ACCESS)

For each `Effect: Allow` statement in the queue policy, classify the
principal scope:

- **WILDCARD_PRINCIPAL** — `Principal: "*"`, `Principal: {"AWS": "*"}`, or
  any construct resolving to all AWS principals.

- **NAMED_PRINCIPAL** — `Principal: {"AWS": "arn:aws:iam::ACCOUNT:role/..."}`
  or `Principal: {"Service": "s3.amazonaws.com"}`.

A WILDCARD_PRINCIPAL statement is classified by its **condition strength**:

**STRONG conditions (NOT public — access is genuinely scoped):**
- `aws:SourceArn` (`ArnEquals` / `ArnLike`) — request must originate from
  the named resource (S3 bucket, SNS topic). This is the standard S3/SNS-
  to-SQS pattern. The caller cannot forge this; it is set by the AWS
  service layer.
- `aws:SourceAccount` (`StringEquals`) — request must originate from the
  named account.
- `aws:SourceAws` (deprecated alias of SourceAccount).

**WEAK / NO conditions (PUBLIC — flag as PUBLIC_ACCESS):**
- No `Condition` block at all.
- `aws:SourceIp` / `aws:SourceIp` containing `0.0.0.0/0` — IP-based
  restrictions are bypassable; `0.0.0.0/0` is the entire internet.
- `aws:SourceVpce` / `aws:SourceVpc` — VPC-scoped but the VPC endpoint is
  network-reachable from peered connections; treat as WEAK for public-
  exposure classification.
- `aws:Referer`, `aws:UserAgent` — trivially forgeable by any HTTP client.

**Action sensitivity for WILDCARD_PRINCIPAL with weak/no condition:**

| Action | Severity | Why |
|---|---|---|
| `sqs:SendMessage` | **CRITICAL** | Any account can inject messages — data poisoning, queue flooding, cost amplification. |
| `sqs:ReceiveMessage` | **CRITICAL** | Any account can drain the queue — silent data exfiltration of message payloads. |
| `sqs:DeleteMessage` | **CRITICAL** | Any account can delete messages — silent data loss. |
| `sqs:*` / `*` | **CRITICAL** | Full queue control — inject, drain, delete, reconfigure. |
| `sqs:GetQueueAttributes` / `sqs:GetQueueUrl` | **MEDIUM** | Metadata disclosure only (queue config, approximate message counts). Not PUBLIC_ACCESS verdict — note as advisory. |

If any WILDCARD_PRINCIPAL statement with a sensitive action (SendMessage,
ReceiveMessage, DeleteMessage, sqs:*, *) and a WEAK/NO condition is found,
the queue verdict is **PUBLIC_ACCESS** with **CRITICAL** risk.

### Step 2: Dead-letter queue presence (NO_DLQ)

Evaluate the `RedrivePolicy` attribute (after JSON-parsing the string):

- **Absent / empty / malformed** → **NO_DLQ**. No dead-letter queue is
  configured. Poison-pill messages retry until `MessageRetentionPeriod`
  expires (default 4 days). Every retry is a billable API call. With a high
  `maxReceiveCount` (if somehow set without a DLQ — configuration drift),
  the retry storm can last days.

- **Present but `deadLetterTargetArn` missing** → **NO_DLQ**. The policy
  JSON exists but the DLQ target is absent — the redrive is non-functional.

- **Present with `deadLetterTargetArn`** → proceed to Step 4d (DLQ
  accessibility sub-check).

**FIFO queue special case:** if `FifoQueue: true` and the `deadLetterTargetArn`
points to a standard (non-FIFO) queue, the redrive is INVALID — SQS silently
rejects messages to a standard DLQ from a FIFO source. Flag as NO_DLQ with
note: "DLQ ARN points to a standard queue — FIFO source requires a FIFO DLQ."

### Step 3: Encryption-at-rest (NO_ENCRYPTION)

Evaluate encryption from two attributes:

- **`SqsManagedSseEnabled: true`** → SSE-SQS is active. Encryption is
  satisfied. This is the free, AWS-managed option (AES-256-GCM, FIPS-
  validated). Do NOT flag.

- **`KmsMasterKeyId` set to a key ARN / key ID / alias** → SSE-KMS is
  active. Encryption is satisfied. Note whether the key is AWS-managed
  (`alias/aws/sqs`) or customer-managed (for cost/rotation auditing — route
  to kms-key-policy-auditor for the key policy).

- **Neither set** → **NO_ENCRYPTION**. Message bodies are stored in
  plaintext at rest. Messages are always encrypted in transit (TLS), but
  the at-rest storage is unencrypted. Flag as HIGH risk.

### Step 4: Configuration gaps (CONFIG_GAP sub-checks)

If no higher-severity verdict was triggered (PUBLIC_ACCESS, NO_DLQ,
NO_ENCRYPTION), evaluate the following sub-checks. Each finding is
enumerated; any non-empty finding set produces a **CONFIG_GAP** verdict.

#### Step 4a: maxReceiveCount too low

If `maxReceiveCount` (from the parsed RedrivePolicy) is <= 1:

- **maxReceiveCount: 1** → any transient failure (consumer crash, network
  blip, Lambda throttle, VisibilityTimeout too short) sends the message
  straight to the DLQ on the FIRST delivery attempt. This is almost always
  a misconfiguration — the message never gets a second chance. High false-
  positive DLQ rate.

- **maxReceiveCount: 2-3** with Lambda event source mapping → advisory. The
  Lambda service's batch window adds delay between retries, so 2-3
  invocations may be insufficient for transient downstream failures.

Flag as CONFIG_GAP with MEDIUM risk. Recommended: set to 5-10 for standard
queues, 5-15 for FIFO queues (message-group blocking makes retries cheaper).

#### Step 4b: maxReceiveCount too high

If `maxReceiveCount` > 1000:

- The message retries up to 1000+ times before reaching the DLQ. At a
  VisibilityTimeout of 30s, that is ~8+ hours of retry cycles. Poison-pill
  messages burn compute budget and starve healthy messages in the queue.
  For FIFO queues, the message group is stalled for the entire duration.

Flag as CONFIG_GAP with MEDIUM risk. Recommended: 5-100 for standard queues,
5-20 for FIFO queues.

#### Step 4c: DLQ message-retention period too short

If the DLQ's `MessageRetentionPeriod` < 345600 (4 days):

- Failed messages expire from the DLQ before operations teams can analyse
  and replay them. The DLQ is useless as a diagnostic tool if messages
  vanish before anyone looks. The default retention (4 days / 345600s) is
  already marginal for weekend coverage.

Flag as CONFIG_GAP with MEDIUM risk. Recommended: 1209600 (14 days, the
maximum) for DLQs to ensure weekend/holiday coverage.

If DLQ attributes are not provided in the input, note: "DLQ retention period
not provided — fetch with `aws sqs get-queue-attributes --queue-url <dlq-url>
--attribute-names MessageRetentionPeriod` to verify."

#### Step 4d: Cross-account DLQ accessibility

If the `deadLetterTargetArn` in the RedrivePolicy points to a queue in a
different AWS account (12-digit account ID differs from the source queue's
account):

- The DLQ is cross-account. SQS supports this IF the DLQ's queue policy (or
  `RedriveAllowPolicy`) grants `sqs:SendMessage` to the source queue's
  account. If no such grant is visible, the redrive is non-functional —
  messages attempting to move to the DLQ will be silently dropped.

- Verify the DLQ's `RedriveAllowPolicy` includes the source queue ARN under
  `redrivePermission: "byQueue"` or `redrivePermission: "allowAll"`.

Flag as CONFIG_GAP with MEDIUM risk. Note: "Cross-account DLQ — verify DLQ
queue policy grants SendMessage to source account."

### Step 5: OK — aggregation

If no findings from Steps 1-4:

```text
QUEUE: <queue-url>
VERDICT: OK
REASON: <queue-name> has a DLQ configured (maxReceiveCount=<N>), encryption-at-rest
  enabled (<SSE-SQS|SSE-KMS>), no public queue-policy exposure, and retention
  periods within recommended bounds.
RISK: LOW
REMEDIATION: None required.
```

## Output format (per queue)

```text
QUEUE: <queue-url or name>
VERDICT: PUBLIC_ACCESS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
RISK: CRITICAL | HIGH | MEDIUM | LOW
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public access with DLQ configured

```text
QUEUE: https://sqs.us-east-1.amazonaws.com/111111111111/billing-events
VERDICT: PUBLIC_ACCESS
REASON: Queue policy Statement "OpenSend" grants sqs:SendMessage to
  Principal:"*" with no restrictive condition — any AWS account can inject
  messages into the billing queue (Step 1).
RISK: CRITICAL
FINDINGS:
  - [CRITICAL] Principal:"*" + sqs:SendMessage with no condition (Step 1) — any account can poison the queue
  - [OK] RedrivePolicy configured with maxReceiveCount=5 (Step 2)
  - [OK] SSE-SQS encryption enabled (Step 3)
REMEDIATION:
  1. Remove the "OpenSend" statement or add aws:SourceArn / aws:SourceAccount
     to scope access to the trusted producer.
  2. Back up the current queue policy before changes:
     aws sqs get-queue-attributes --queue-url <url> --attribute-names Policy
     --output json > /tmp/<queue>-policy-backup.json.
```

## Edge-case handling

- **`Principal: "*"` + `aws:SourceArn` (S3/SNS notification pattern).** This
  is the standard cross-service integration pattern and is NOT public
  access. The `aws:SourceArn` condition is set by the AWS service layer
  (S3, SNS, EventBridge) and restricts access to the named resource. Verify
  the SourceArn is a specific bucket/topic ARN, not a wildcard pattern
  (`arn:aws:s3:::*`). Classify as OK for this dimension.

- **`Principal: "*"` + `aws:SourceAccount`.** Same logic — the condition
  restricts access to a specific account. STRONG. Not public.

- **Empty queue policy (`Policy` absent).** This is the SECURE default. With
  no resource-based policy, only IAM identity-based policies govern access.
  Do NOT flag a missing Policy attribute as a gap.

- **DLQ itself has no DLQ.** A dead-letter queue should NOT have its own
  redrive policy (infinite redrive chain). If the DLQ has a RedrivePolicy,
  note as advisory: "DLQ has its own RedrivePolicy — this creates a
  redrive chain. Remove the DLQ's RedrivePolicy."

- **FIFO queue with standard DLQ.** SQS rejects this at configuration time,
  but if the attribute snapshot shows it (stale config), flag as NO_DLQ:
  "FIFO source queue cannot use a standard DLQ — the DLQ must also be FIFO."

- **`RedrivePolicy` with `maxReceiveCount` as integer vs string.** The CLI
  returns `maxReceiveCount` as a string (`"5"`). CloudFormation may set it
  as an integer (`5`). Accept both forms in classification.

- **Multiple statements, some public some not.** The queue-level verdict is
  driven by the **worst** statement. A queue with one safe statement
  (named principal) and one public statement (wildcard, no condition) is
  PUBLIC_ACCESS — the public statement exposes the queue regardless of the
  safe one.

## Anti-Patterns — NEVER

- NEVER classify `Principal: "*"` with a STRONG condition (`aws:SourceArn`,
  `aws:SourceAccount`) as PUBLIC_ACCESS. This is the standard S3/SNS-to-SQS
  notification pattern. The condition is set by the AWS service layer and
  the caller cannot forge it. Flagging it as public is a false positive that
  causes unnecessary policy churn and erodes trust in the audit.

- NEVER classify a queue with `SqsManagedSseEnabled: true` as NO_ENCRYPTION.
  SSE-SQS provides AES-256-GCM encryption at rest, is FIPS-validated, and
  satisfies SOC2 / PCI-DSS / HIPAA at-rest encryption requirements. It is
  functionally equivalent to SSE-KMS for encryption purposes — the
  difference is key management (AWS-managed vs customer-managed), not
  encryption strength.

- NEVER recommend `maxReceiveCount: 1`. A single transient failure (consumer
  crash, Lambda throttle, VisibilityTimeout too short, network blip) sends
  the message irretrievably to the DLQ. The minimum recommended value is 3
  for standard queues, 5 for FIFO queues (where message-group blocking
  makes each retry more expensive).

- NEVER flag a missing `Policy` attribute as a security gap. The absence of
  a resource-based queue policy means access is governed solely by IAM
  identity-based policies — this is the SECURE default. Only flag the
  PRESENCE of a permissive policy.

- NEVER recommend the legacy `Redrive` API (deprecated 2022) for moving
  messages back from the DLQ. Use `aws sqs start-message-move-task
  --source-arn <dlq-arn> --destination-arn <source-arn>` (the current
  asynchronous redrive API).

- NEVER assume `RedrivePolicy` is a native dict. It is a JSON-encoded
  string in the API response. Reading `policy["deadLetterTargetArn"]`
  directly on the unparsed string returns `None` / throws — producing a
  false NO_DLQ verdict. Always JSON-parse the inner string first.

- NEVER treat `aws:SourceVpce` as a STRONG condition for public-access
  classification. VPC endpoints can be reachable from peered VPCs, VPN
  connections, and Transit Gateway attachments. Unlike `aws:SourceArn`
  (set by the AWS service layer), VPC endpoint identity is
  network-adjacent and more easily bypassed. Treat as WEAK.

- NEVER set `maxReceiveCount` above 1000 without explicit justification. At
  a 30-second VisibilityTimeout, 1000 retries = 8+ hours of poison-pill
  cycling. For FIFO queues, this means 8+ hours of message-group stall.

- NEVER recommend a DLQ `MessageRetentionPeriod` below 4 days. Operations
  teams need time to analyse and replay failed messages. The SQS minimum is
  60 seconds; the maximum is 1209600 seconds (14 days). Use 14 days for
  DLQs to ensure weekend and holiday coverage.

- NEVER ignore the FIFO DLQ type constraint. A FIFO queue's DLQ must also be
  FIFO. A standard DLQ silently fails to receive redriven messages from a
  FIFO source — the poison pill stays in the source queue forever.

- NEVER assume the queue policy is the complete access picture. SQS access
  is governed by the INTERSECTION of IAM identity-based policies AND the
  resource-based queue policy (for cross-account) or EITHER (for same-
  account). A queue with no resource-based policy may still be accessible
  via IAM. The audit evaluates the resource-based policy for public
  exposure — it does not enumerate all IAM principals.

- NEVER recommend SSE-KMS over SSE-SQS purely for "better security" without
  explaining the trade-off. SSE-KMS adds per-API KMS cost (~$0.03/10k
  requests + KMS key cost), potential throttle from KMS rate limits, and
  latency from the KMS decrypt call. SSE-SQS is sufficient unless you need
  customer-managed key control, CloudTrail decrypt logging, or key-level
  grant revocation.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (SetQueueAttributes, RemovePermission, AddPermission, PurgeQueue,
  DeleteQueue, StartMessageMoveTask), the auditor MUST emit:
  `CONFIRM: About to <action> on queue <url>. This affects <consequence>.
  Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Back up the current queue policy and attributes before modification.**
  Queue policies are not versioned — there is no rollback without a backup.
  ```bash
  aws sqs get-queue-attributes --queue-url <url> \
    --attribute-names All --output json > /tmp/<queue>-attrs-backup-$(date +%s).json
  ```

- **PurgeQueue is destructive and irreversible.** `aws sqs purge-queue`
  deletes ALL messages in the queue instantly (up to the purge limit). It
  cannot be scoped to specific messages. NEVER recommend PurgeQueue as a
  remediation for poison-pill messages — use StartMessageMoveTask to move
  them to the DLQ instead.

- **SetQueueAttributes replaces, not merges.** Setting `Policy` via
  `SetQueueAttributes` replaces the ENTIRE queue policy. If the new policy
  omits a statement that a producer depends on, that producer silently
  loses access. Always diff the old and new policy before applying.

- **For PUBLIC_ACCESS findings (CRITICAL):** treat as incident-response.
  An attacker may have already injected or exfiltrated messages. After
  remediation, audit CloudTrail for `sqs:SendMessage` /
  `sqs:ReceiveMessage` events from unexpected principals during the
  exposure window. Messages that were exfiltrated should be considered
  compromised — rotate any credentials or tokens that were in message
  bodies.

- Prefer additive changes (add a Deny statement, add a Condition) over
  destructive changes (remove a statement). Additive changes are reversible
  and do not risk breaking existing producers/consumers.

## Remediation guidance

### For PUBLIC_ACCESS — Principal:"*" with no condition (Step 1)

1. **Immediately** remove the wildcard principal or add a STRONG condition
   (`aws:SourceArn`, `aws:SourceAccount`). Back up the policy first.
2. If the queue receives messages from a known S3 bucket or SNS topic,
   replace `Principal: "*"` with `Principal: "*"` + `Condition:
   ArnEquals: {aws:SourceArn: "<bucket/topic-arn>"}`.
3. If only specific accounts should access the queue, replace
   `Principal: "*"` with `Principal: {"AWS": "<account-role-arn>"}`.
4. **Assume breach.** Audit CloudTrail for `sqs:ReceiveMessage` /
   `sqs:SendMessage` from unexpected principals. Rotate any credentials
   that were in message payloads.

```bash
# Back up current policy
aws sqs get-queue-attributes --queue-url <url> \
  --attribute-names Policy --output json > /tmp/<queue>-policy-backup.json

# Apply scoped policy (add aws:SourceArn condition)
aws sqs set-queue-attributes --queue-url <url> \
  --attributes Policy=<new-scoped-policy-json>
```

### For NO_DLQ — no dead-letter queue configured (Step 2)

1. Create a DLQ (same account, same region, same FIFO type):
   ```bash
   aws sqs create-queue --queue-name <queue-name>-dlq.fifo \
     --attributes FifoQueue=true
   ```
2. Set the RedrivePolicy on the source queue:
   ```bash
   DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <dlq-url> \
     --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
   aws sqs set-queue-attributes --queue-url <source-url> \
     --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
   ```
3. Set the DLQ's MessageRetentionPeriod to 14 days (1209600 seconds):
   ```bash
   aws sqs set-queue-attributes --queue-url <dlq-url> \
     --attributes MessageRetentionPeriod=1209600
   ```

### For NO_ENCRYPTION — neither SSE-SQS nor SSE-KMS (Step 3)

1. Enable SSE-SQS (free, immediate, no application impact — no re-
   encryption needed because SQS encrypts transparently):
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes SqsManagedSseEnabled=true
   ```
2. For customer-managed key control (compliance requirement), use SSE-KMS:
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes KmsMasterKeyId=alias/my-sqs-key,KmsDataKeyReusePeriodSeconds=300
   ```
3. SSE-KMS requires the key policy to grant `kms:Decrypt` /
   `kms:GenerateDataKey*` to `sqs.<region>.amazonaws.com` service
   principal. Route to kms-key-policy-auditor for the key policy audit.

### For CONFIG_GAP — maxReceiveCount tuning (Steps 4a/44b)

1. Adjust maxReceiveCount (recommended: 5-10 standard, 5-15 FIFO):
   ```bash
   aws sqs set-queue-attributes --queue-url <url> \
     --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
   ```
2. If consumers are Lambda functions, verify the event source mapping's
   `VisibilityTimeout` is >= the function's p99 duration:
   ```bash
   aws lambda list-event-source-mappings --function-name <fn> \
     --query 'EventSourceMappings[].{Arn:EventSourceArn,VT:VisibilityTimeout}'
   ```

### For CONFIG_GAP — DLQ retention too short (Step 4c)

```bash
aws sqs set-queue-attributes --queue-url <dlq-url> \
  --attributes MessageRetentionPeriod=1209600
```

### For CONFIG_GAP — cross-account DLQ (Step 4d)

1. Verify the DLQ's RedriveAllowPolicy grants access to the source queue:
   ```bash
   aws sqs get-queue-attributes --queue-url <dlq-url> \
     --attribute-names RedriveAllowPolicy
   ```
2. If missing, set it:
   ```bash
   aws sqs set-queue-attributes --queue-url <dlq-url> \
     --attributes RedriveAllowPolicy='{"redrivePermission":"byQueue","sourceQueueArns":["arn:aws:sqs:us-east-1:111111111111:source-queue"]}'
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend enabling DLQ CloudWatch alarms (ApproximateNumberOfMessagesDelayed
   > 0) for early poison-pill detection.
3. For FIFO queues, recommend monitoring message-group age via the
   `ApproximateAgeOfOldestMessage` CloudWatch metric.

## Recent AWS features (2024-2026)

- **SQS paused queues (2024):** SQS now supports pausing message delivery without deleting messages. Auditors should verify that production queues are not inadvertently paused — a paused queue silently stops message consumption.
- **Message retention period increase (2024):** SQS now supports message retention up to 14 days (previously 4 days). Auditors should verify that retention periods are appropriate — excessive retention on high-throughput queues can cause cost accumulation.
- **SSE-SQS vs SSE-KMS (2024):** SQS now supports server-side encryption with SQS-managed keys (SSE-SQS) as a simpler alternative to SSE-KMS. Auditors should verify which encryption mode is in use — SSE-KMS provides customer-controlled keys but requires KMS key policy management, while SSE-SQS is simpler but less granular.
- **Dead-letter queue redrive (2024-2025):** SQS now supports `StartMessageMoveTask` API for redriving messages from DLQ back to the source queue. Auditors should verify that redrive operations are logged in CloudTrail and that redriven messages do not cause duplicate processing.

## Domain

AWS CloudOps / App Integration — SQS Messaging Security & Reliability.
