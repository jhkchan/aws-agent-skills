---
name: eventbridge-bus-policy-auditor
description: >-
  Audits AWS EventBridge event buses for public event-injection exposure
  (Principal:* or cross-account with events:PutEvents and no strong
  condition), missing dead-letter queues on rule targets, absent
  customer-managed KMS encryption, and archive/enrichment gaps. Emits a
  deterministic verdict (PUBLIC_BUS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP |
  OK) per bus with enumerated findings and specific remediation. Use when
  reviewing EventBridge bus policies, checking for public event injection,
  validating DLQ coverage on rules, auditing KMS encryption posture, or
  hardening event-bus security before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy-document classification.
  Live-account audits use aws events describe-event-bus, aws events
  list-rules, aws events list-targets-by-rule, aws events list-archives,
  and aws events describe-rule (AWS CLI v2, SSO or key-based credentials).
keywords:
  - EventBridge
  - event bus
  - bus policy
  - events:PutEvents
  - event injection
  - cross-account
  - wildcard permissions
  - dead-letter queue
  - DLQ
  - KMS encryption
  - customer-managed key
  - KmsKeyIdentifier
  - archive
  - schema discovery
  - event replay
  - aws:PrincipalOrgID
  - rule targets
  - DeadLetterConfig
  - PutPermission
  - Principal:"*"
tags: [eventbridge, security, event-bus, app-integration, dlq, encryption, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  verdict_shape: "PUBLIC_BUS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an EventBridge event bus policy before production deployment,
    checking for public or cross-account event injection, validating DLQ
    coverage on rule targets, auditing KMS encryption posture, inspecting
    archive or schema-discovery configuration, or hardening event-bus
    security across an account.
  activation_triggers:
    - "audit this event bridge bus"
    - "is my event bus public"
    - "check eventbridge bus policy"
    - "event injection risk"
    - "missing DLQ on rule"
    - "is event bridge encrypted"
    - "event bus cross-account"
    - "Principal star eventbridge"
    - "dead-letter queue check"
    - "event bridge archive gap"
  invocation_schema: >-
    Input: either (a) an event bus policy JSON document, optionally paired
    with bus metadata (KmsKeyIdentifier), rule/target configs, and
    archive status, OR (b) a bus name/ARN for live-account audit. Output:
    deterministic BUS/VERDICT/REASON/FINDINGS/REMEDIATION block per bus,
    where VERDICT is one of PUBLIC_BUS, NO_DLQ, NO_ENCRYPTION,
    CONFIG_GAP, OK.
---

# EventBridge Bus Policy Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and `events:PutEvents` is the EventBridge analogue of
`kms:Decrypt` — one permission grants injection access to every rule and
downstream target on the bus.

An EventBridge event bus is the ingestion gate for event-driven
automation. Three properties make it uniquely dangerous when
misconfigured:

- `events:PutEvents` is an **event-injection vector**: one permission
  lets an attacker craft events that match rule patterns and trigger
  Lambda, Step Functions, SQS, ECS, and API-destination targets. The
  blast radius extends through every rule on the bus.
- Missing `DeadLetterConfig` is a **silent data-loss vector**: failed
  invocations exhaust retries (6 hours for Lambda/SQS, 24 hours for API
  destinations) then disappear permanently — no DLQ, no trace.
- The bus policy is **ingestion-gate only**; rule event-patterns are
  the **routing-gate**. Both planes must be audited. A locked-down bus
  policy with a permissive event pattern still routes any ingested event.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `Principal: "*"` + `events:PutEvents`/`events:*`/`*` + no/weak condition | **PUBLIC_BUS** | Step 5a |
| Cross-account + `events:PutEvents` + no/weak condition | **PUBLIC_BUS** | Step 5b |
| `Principal: "*"` + `events:PutRule`/`events:PutPermission` + no/weak condition | **PUBLIC_BUS** | Step 5c |
| Any rule target missing `DeadLetterConfig` | **NO_DLQ** | Step 6 |
| `KmsKeyIdentifier` absent on custom bus | **NO_ENCRYPTION** | Step 7 |
| No archive configured on the bus | **CONFIG_GAP** | Step 8 |
| Scoped principals + STRONG condition + DLQ + CMK + archive | **OK** | Step 9 |
| `Principal: "*"` + PutEvents + STRONG condition (`aws:PrincipalOrgID`, `aws:SourceAccount`) | OK on policy dimension (condition-scoped, not public) | Step 5d |

Severity ordering for aggregation: **PUBLIC_BUS > NO_DLQ > NO_ENCRYPTION
> CONFIG_GAP > OK**.

## Pre-flight: bus metadata gate

Before evaluating the policy, classify the bus itself. Several attributes
short-circuit the audit.

| Attribute | Value | Effect |
|---|---|---|
| `Name` | `default` | **Default event bus.** Receives all AWS service events (CloudWatch, EC2, GuardDuty, Security Hub) by default. Restricting its policy may **break service event delivery**. Do NOT flag same-account service-principal statements on the default bus. Still audit DLQ, encryption, and archive dimensions. |
| `Name` | (custom) | Proceed with full audit. Custom buses are where restrictive policies apply. |
| `KmsKeyIdentifier` | (absent) | Bus uses an **AWS-owned key** (not even AWS-managed — invisible to your KMS console, no rotation control, no CloudTrail data-event logging). This is the NO_ENCRYPTION finding (Step 7). |
| `KmsKeyIdentifier` | `arn:aws:kms:...` | Customer-managed key configured. Encryption dimension passes. |

**Multi-bus / account-wide sweep note (pagination):** `aws events
list-event-buses` returns at most 100 per page. `aws events list-rules`
returns at most 100 per page per bus. `aws events list-targets-by-rule`
returns at most 50 per page. All three silently truncate — always drain
`NextToken` to completion. A bus with 120 rules silently drops 20 from
the first page.

**If the bus policy JSON is malformed** (invalid JSON, missing
`Statement`, missing `Principal` or `Action`), output:

```text
BUS: <bus-name>
VERDICT: ERROR
REASON: Bus policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws events describe-event-bus --name <bus> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious EventBridge behaviors

These behaviors change classification if ignored:

- **`events:PutEvents` is the blast-radius multiplier.** One permission
  grants event injection that can trigger every rule on the bus — Lambda,
  Step Functions, SQS, ECS tasks, API destinations. An attacker who can
  PutEvents can craft events matching your rule patterns and drive
  downstream automation. This is not "broad access" — it is a direct
  control-plane injection vector.

- **The bus policy is ingestion-gate; rule event-patterns are
  routing-gate.** The bus policy controls WHO can PutEvents. The rule
  `EventPattern` controls WHICH events trigger targets. A locked bus
  policy is necessary but not sufficient — a permissive event pattern
  (e.g., `{"source": [{"prefix": ""}]}`) routes any ingested event. The
  policy audit evaluates ingestion exposure; rule-pattern audit evaluates
  routing exposure.

- **`events:source` and `detail-type` are event-body fields, NOT IAM
  condition keys.** A bus policy condition using
  `StringEquals: {"events:source": "my.app"}` is a **silent no-op** — it
  does not restrict anything. Only `aws:SourceAccount`, `aws:SourceArn`,
  `aws:PrincipalAccount`, and `aws:PrincipalOrgID` are valid bus-policy
  condition keys. Restricting by event source must be done at the rule
  `EventPattern` level, not in the bus policy.

- **Same-account PutEvents does not require the bus policy.** The account
  root implicitly has access — same-account principals can PutEvents even
  with an empty or restrictive bus policy. The bus policy is for
  cross-account and service-principal delegation. A same-account-only
  statement is NORMAL (analogous to KMS's root-of-trust statement).

- **`Principal: {"Service": "..."}` is NORMAL for AWS service
  integration.** Services like `cloudwatch.amazonaws.com`,
  `guardduty.amazonaws.com`, `ssm.amazonaws.com` publish events. These
  service principals should NOT be flagged as public exposure — they are
  AWS-controlled and required for service-to-bus delivery.

- **`Resource` in a bus policy is effectively always the bus ARN or
  `"*"`.** The policy IS attached to the bus — `Resource: "*"` and
  `Resource: <bus-arn>` are functionally identical. Do not treat a scoped
  `Resource` element as a restriction; evaluate `Principal` + `Action` +
  `Condition` only.

- **Cross-account PutEvents requires intersection.** The bus policy AND
  the caller's identity-based policy must BOTH allow. A bus policy
  allowing cross-account PutEvents is necessary but the external
  principal's IAM must also permit it. Still flag it — the bus policy is
  the resource owner's controlled gate.

- **DeadLetterConfig is per-TARGET, not per-rule or per-bus.** A rule can
  have up to 5 targets (300 rules per bus). Each target independently
  needs a DLQ ARN (`DeadLetterConfig.arn`). Missing DLQ on ANY target
  means that target's failed invocations are silently dropped after the
  retry window exhausts.

- **Retry windows differ by target type.** Lambda, SQS, SNS, ECS, and
  Step Functions targets retry for ~6 hours (185 attempts with
  exponential backoff). API destinations retry for up to 24 hours with
  `MaximumEventAgeInSeconds` (default 900s) and `MaxRetryAttempts`
  (default 3). After exhaustion: DLQ captures the event (if configured),
  otherwise permanent silent loss.

- **`KmsKeyIdentifier` absent = AWS-owned key.** EventBridge encrypts at
  rest by default with an AWS-owned key — invisible in your KMS console,
  no rotation control, no CloudTrail data-event logging on Decrypt. A
  customer-managed key (`KmsKeyIdentifier` set to a CMK ARN) gives
  rotation control, key-policy control, and decrypt-audit capability.
  Absence of CMK is the NO_ENCRYPTION finding.

- **`StartReplay` sends archived events to ALL rules matching the
  pattern — including rules created AFTER the original events.** This can
  cause unexpected duplicate processing. An audit should verify archive
  exists (for replay capability) but also note the replay semantics.

- **Bus policy size limit is 8,192 characters (8 KiB).** `put-permission`
  replaces the entire policy atomically — no version history, no diff,
  no rollback. The only recovery is a manual backup.

- **`aws:PrincipalOrgID` is the strongest org-scoped condition.** It
  scopes to all accounts within an AWS Organization — better than
  enumerating individual `aws:SourceAccount` values for large orgs.
  Unlike IAM role trust policies, EventBridge bus policies do NOT
  support `sts:ExternalId` — the confused-deputy defense for EventBridge
  is `aws:PrincipalOrgID` or `aws:SourceAccount`, never ExternalId.

- **Same-account callers bypass the bus policy entirely.** When a
  same-account principal calls `PutEvents` with `--event-bus-name
  <bus>`, the root's implicit access applies — no bus-policy statement
  is needed. The bus policy is ONLY relevant for cross-account and
  service-principal delegation. A bus with an empty policy still allows
  all same-account principals to publish.

- **Event bus ARNs are predictable — the name is not a secret.** The
  ARN pattern `arn:aws:events:<region>:<account>:event-bus/<name>` is
  fully deterministic from account ID, region, and bus name. An attacker
  who knows these three values (easily discovered via social engineering
  or enumeration) can target PutEvents. There is no way to "hide" a bus.

- **`PutEvents` accepts up to 10 events per API call, each up to 256 KB
  (2 MB total request).** An attacker with wildcard PutEvents can inject
  high-volume event bursts — each event triggers independent rule
  evaluation. Rate-limit your bus via EventBridge quotas (transaction
  limit) and consider input transformation validation on rules.

- **API destination auth credentials expire silently.** OAuth
  client-credential tokens refresh automatically, but API-key and
  basic-auth credentials do NOT — a rotated or revoked credential causes
  silent delivery failure with no CloudTrail signal until the DLQ (if
  configured) fills. Monitor `InvocationHttpStatusCode` in CloudTrail
  metrics for API destinations.

### Step 1: Bus type classification

If the bus is the **default bus** (`Name: default`):
- Do NOT flag same-account `Principal: {"Service": "..."}` statements —
  AWS services must publish to the default bus for built-in integrations.
- Still evaluate DLQ, encryption, and archive dimensions normally.
- Flag `Principal: {"AWS": "*"}` + PutEvents on the default bus as
  PUBLIC_BUS — anyone can inject into the bus that receives all AWS
  service events, compounding the injection surface.

If the bus is a **custom bus**, proceed with full policy audit.

### Step 2: Principal scope classification

For each `Effect: Allow` statement in the bus policy:

- **WILDCARD_PRINCIPAL** — Principal is `"*"`, `{"AWS": "*"}`, or any
  construct resolving to all AWS principals.

- **CROSS_ACCOUNT** — Principal includes an ARN whose 12-digit account
  differs from the bus's owning account.

- **SERVICE_PRINCIPAL** — Principal is `{"Service": "<service-id>"}`.
  This is NORMAL for AWS service-to-bus integration. Do NOT flag as
  public unless the service principal is paired with dangerous admin
  actions (PutRule, PutPermission) without conditions.

- **SAME_ACCOUNT** — All principals share the bus's owning account.
  This includes root (`arn:aws:iam::ACCOUNT:root`) and same-account
  roles/users.

A statement with BOTH same-account and cross-account/wildcard principals
is classified by the **widest** scope.

### Step 3: Action danger classification

| Danger level | Actions | Why |
|---|---|---|
| **INJECT** | `events:PutEvents`, `events:*`, `*` | Event injection — can trigger every rule and downstream target. Blast-radius multiplier. |
| **ADMIN** | `events:PutRule`, `events:DeleteRule`, `events:PutTargets`, `events:RemoveTargets`, `events:PutPermission`, `events:RemovePermission`, `events:DisableRule`, `events:EnableRule`, `events:UpdateArchive` | Can modify bus configuration, inject new rules, revoke existing rules, or change the policy. |
| **READ** | `events:List*`, `events:Describe*`, `events:TestEventPattern` | Metadata disclosure — enumerates rules, targets, and bus configuration. |

`NotAction` in an Allow is an inverse wildcard — grants every EventBridge
action EXCEPT the listed ones. Treat as INJECT + ADMIN (worst case).

### Step 4: Condition strength evaluation

**STRONG conditions (policy dimension passes — condition-scoped, not public):**
- `aws:PrincipalOrgID` with `StringEquals` — scopes to all accounts in
  the named Organization. The strongest multi-account condition.
- `aws:SourceAccount` with `StringEquals` — request must originate from
  the named account.
- `aws:SourceArn` with `StringEquals`/`StringLike` — request must
  originate from the named resource.
- `aws:PrincipalAccount` — equivalent to SourceAccount.

**WEAK conditions (do NOT pass — treat as no condition, still PUBLIC_BUS):**
- `aws:SourceIp` — IP-based restrictions are bypassable by callers who
  control their egress (NAT gateway, proxy, VPN). **Quantitative
  prefix-length threshold:** a CIDR with `/0` suffix (`0.0.0.0/0`,
  `::/0`) covers the entire internet — equivalent to no condition. `/8`
  or broader (16M+ addresses) is effectively unrestricted. Only `/28`
  or narrower (16 or fewer addresses) provides operationally meaningful
  scoping. Between `/8` and `/28`, evaluate whether the CIDR covers
  known NAT, proxy, or cloud-egress ranges.
- `aws:Referer`, `aws:UserAgent` — trivially forgeable.
- `events:source`, `events:detail-type` — NOT valid condition keys;
  silently ignored by IAM evaluation.

### Step 5: Policy severity matrix — PUBLIC_BUS determination

Evaluate each Allow statement by combining principal scope (Step 2),
action danger (Step 3), and condition strength (Step 4):

| Rule | Principal | Action | Condition | → PUBLIC_BUS? |
|---|---|---|---|---|
| 5a | WILDCARD | INJECT | None/weak | **Yes — PUBLIC_BUS** (anyone can inject events) |
| 5b | CROSS_ACCOUNT | INJECT | None/weak | **Yes — PUBLIC_BUS** (external account can inject) |
| 5c | WILDCARD or CROSS | ADMIN | None/weak | **Yes — PUBLIC_BUS** (external principal can inject/modify rules) |
| 5d | WILDCARD or CROSS | INJECT/ADMIN | STRONG | **No — OK on policy dimension** (condition-scoped, not public) |
| 5e | WILDCARD or CROSS | READ | Any | **No** — metadata-only exposure (note as low-severity finding) |
| 5f | SERVICE_PRINCIPAL | INJECT | None | **No** — normal service integration (Step 1) |
| 5g | SAME_ACCOUNT | Any | Any | **No** — implicit access; IAM is the second gate |

**CRITICAL CLASSIFICATION RULE — Step 5d:** A `Principal: "*"` or
cross-account grant with `events:PutEvents` and a STRONG condition
(`aws:PrincipalOrgID`, `aws:SourceAccount`, `aws:SourceArn`) is
**NOT PUBLIC_BUS**. The condition scopes access to a known organization
or account. Classify the policy dimension as **OK** and note the
condition-restricted access in FINDINGS for verification. Do NOT
conflate "cross-account" with "public" — a condition-restricted
cross-account grant is a controlled delegation, not an open injection
vector. This is the single most common classification error.
| 5e | WILDCARD or CROSS | READ | Any | **No** — metadata-only exposure (note as low-severity finding) |
| 5f | SERVICE_PRINCIPAL | INJECT | None | **No** — normal service integration (Step 1) |
| 5g | SAME_ACCOUNT | Any | Any | **No** — implicit access; IAM is the second gate |

If any statement matches 5a/5b/5c, the **PUBLIC_BUS** verdict is emitted
for the policy dimension.

**Special case — the account-root statement:** A statement with
`Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `events:*` is the
default root-delegation pattern. It delegates bus management to the
account's IAM policies. This is **NORMAL** — do NOT flag it. Same-account
PutEvents does not require the bus policy (implicit root access).

### Step 6: Dead-letter queue evaluation

For each rule on the bus, enumerate ALL targets via
`list-targets-by-rule`. For each target, check `DeadLetterConfig`:

- **DeadLetterConfig absent on ANY target** → **NO_DLQ** finding for that
  target. Failed invocations exhaust retries (6h Lambda/SQS/SNS/ECS/SFN,
  up to 24h API destinations) then are permanently lost — no DLQ, no
  trace. This is a silent data-loss vector.

- **DeadLetterConfig present (SQS ARN)** → target passes the DLQ check.
  Verify the SQS queue exists and has a retention period long enough for
  operational response (>= 4 days recommended).

A bus with multiple rules where ALL targets have DLQs passes this step.
A single target without DLQ is enough for the NO_DLQ finding.

**Quota note:** A rule can have up to 5 targets. Each target needs its
own DLQ ARN — sharing one SQS queue across targets is acceptable but
complicates triage (all failures land in one queue).

### Step 7: KMS encryption evaluation

Check `KmsKeyIdentifier` on the bus metadata:

- **KmsKeyIdentifier absent** → **NO_ENCRYPTION** finding. The bus uses
  an AWS-owned key — invisible in your KMS console, no rotation control,
  no key policy control, no CloudTrail data-event logging on decrypt.
  A customer-managed key gives rotation control, key-policy control, and
  decrypt-audit capability.

- **KmsKeyIdentifier set to a CMK ARN** → encryption dimension passes.
  Verify the referenced CMK exists, is enabled, and has rotation enabled
  (cross-reference to kms-key-policy-auditor for the key policy audit).

### Step 8: Archive and enrichment evaluation

Check archive and schema-discovery status:

- **No archive configured** → **CONFIG_GAP** finding. Without an archive,
  there is no event-replay capability for incident recovery. Archives
  capture events matching a pattern for a configurable retention period.
  Recommend `CreateArchive` with a broad event pattern.

- **Archive present** → passes. Note the retention period and event
  pattern coverage (a narrow pattern may miss events you need to replay).

- **Schema discovery disabled** → note as a low-priority CONFIG_GAP
  sub-finding. Without schema discovery, you lose automated schema
  inference and code-generation benefits. Enable via
  `UpdateEventBus` with schema-discovery on.

### Step 9: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all dimensions,
where PUBLIC_BUS > NO_DLQ > NO_ENCRYPTION > CONFIG_GAP > OK:

```text
verdict = max(policy_finding, dlq_finding, encryption_finding, archive_finding)
```

If no findings across all dimensions, the verdict is **OK**.

## Output format (per bus)

```text
BUS: <bus-name or ARN>
VERDICT: PUBLIC_BUS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [PUBLIC_BUS] <finding description (Step Na)>
  - [NO_DLQ] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public bus with missing DLQ

```text
BUS: custom-bus-app-events
VERDICT: PUBLIC_BUS
REASON: Statement "OpenIngest" grants events:PutEvents to Principal "*"
with no restrictive condition — any AWS account holder can inject events
that trigger all rules on the bus (Step 5a). Rule "alert-rule" target
"lambda-handler" is also missing a dead-letter queue.
FINDINGS:
  - [PUBLIC_BUS] Principal "*" + events:PutEvents + no condition (Step 5a)
  - [NO_DLQ] Rule "alert-rule" target "lambda-handler" has no DeadLetterConfig (Step 6)
  - [NO_ENCRYPTION] KmsKeyIdentifier absent — bus uses AWS-owned key (Step 7)
  - [CONFIG_GAP] No archive configured — no replay capability (Step 8)
REMEDIATION:
  1. PUBLIC_BUS — Replace Principal "*" with specific account/role ARNs.
     Add aws:PrincipalOrgID or aws:SourceAccount condition to scope access.
  2. NO_DLQ — Create an SQS DLQ and attach to each target:
     aws events put-targets --rule alert-rule --event-bus-name custom-bus-app-events
       --targets '[{"Id":"lambda-handler","Arn":"...","DeadLetterConfig":{"Arn":"arn:aws:sqs:...:dlq"}}]'
  3. NO_ENCRYPTION — Associate a customer-managed KMS key:
     aws events update-event-bus --name custom-bus-app-events
       --kms-key-identifier arn:aws:kms:us-east-1:111111111111:key/cmk-id
  4. CONFIG_GAP — Create an archive:
     aws events create-archive --archive-name app-events-archive
       --event-source-name custom-bus-app-events --retention 30
```

## Anti-Patterns — NEVER

- NEVER classify `Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` +
  `events:*` as a vulnerability. This is the **default root-delegation
  statement**. Same-account access does not require the bus policy — the
  root has implicit access. Flagging it as WILDCARD is a false positive.

- NEVER flag `Principal: {"Service": "guardduty.amazonaws.com"}` or any
  AWS service principal with `events:PutEvents` as public exposure on
  the **default bus**. AWS services must publish to the default bus for
  built-in integrations. This is normal service-to-bus delivery.

- NEVER treat `events:source` or `detail-type` as IAM condition keys in a
  bus policy. They are event-body fields — a bus policy condition using
  them is a silent no-op and provides zero restriction. Only
  `aws:SourceAccount`, `aws:SourceArn`, `aws:PrincipalAccount`, and
  `aws:PrincipalOrgID` are valid.

- NEVER classify a `Principal: "*"` + `events:PutEvents` grant with a
  STRONG condition (`aws:PrincipalOrgID`, `aws:SourceAccount`) as
  PUBLIC_BUS. The condition narrows access to a known org/account.
  Classify as OK on the policy dimension — note the condition-restricted
  access in FINDINGS for verification.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a real condition. This
  CIDR is the entire internet and provides zero restriction. Treat the
  statement as if the condition is absent — PUBLIC_BUS.

- NEVER assume one DLQ per rule is sufficient. DeadLetterConfig is
  per-TARGET — a rule with 5 targets needs 5 DLQ ARNs. Missing DLQ on
  any single target is a silent data-loss vector for that target.

- NEVER assume the bus policy is the complete access picture for
  cross-account. Cross-account PutEvents requires BOTH the bus policy
  AND the caller's IAM to allow it (intersection). But always flag the
  bus-policy grant — the resource owner controls this gate.

- NEVER recommend restricting the **default bus** policy without
  explaining that it may break AWS service event delivery. CloudWatch
  Alarms, GuardDuty, Security Hub, EC2, and dozens of other services
  publish to the default bus. Use custom buses for restrictive policies.

- NEVER overlook a rule with zero targets. A rule with no targets
  consumes event-matching capacity (300 rules per bus quota) but
  triggers nothing — it is dead configuration. Flag as CONFIG_GAP.

- NEVER assume archive and schema discovery are enabled by default.
  Archives require explicit `CreateArchive`. Schema discovery requires
  explicit enablement. Both are absent on a freshly created bus.

- NEVER set archive retention > 90 days without a cost justification.
  Archive events are billed per-event-month — a high-volume bus
  (1M events/day) at 90 days costs ~9x more than the recommended 7-30
  day operational window. Use longer retention only for compliance
  requirements and budget-alert the archive.

- NEVER use `put-permission` with a duplicate `--statement-id`. The
  statement-id uniquely identifies the permission entry; reusing an
  existing id **silently overwrites** the prior statement. Always use
  unique, descriptive statement-ids (e.g., `CrossAccountAppPublisher`,
  not `Allow1`).

- NEVER attempt to modify the default bus policy to remediate
  cross-account access without first verifying which AWS service
  integrations depend on it. Breaking service event delivery is an
  active outage.

- NEVER assume `Resource: "*"` in a bus policy is broader than
  `Resource: <bus-arn>`. The policy is attached to the bus — both are
  functionally identical. Evaluate `Principal` + `Action` + `Condition`
  only.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (PutPermission, RemovePermission, PutTargets, UpdateEventBus,
  PutRule, DeleteRule), the auditor MUST emit:
  `CONFIRM: About to <action> on bus <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Back up the current bus policy** before any modification:
  `aws events describe-event-bus --name <bus> --profile <p> --output json > /tmp/<bus>-policy-backup-$(date +%s).json`
  Bus policies have no version history — `put-permission` replaces the
  entire policy atomically. The backup is the only rollback path.

- Before removing a cross-account principal from the bus policy, verify
  the external account's workload is not actively publishing events.
  Check CloudTrail for `events:PutEvents` from the external account in
  the last 7 days. Removing access without coordination causes an
  immediate event-delivery outage for the external publisher.

- Before associating a KMS key (`UpdateEventBus --kms-key-identifier`),
  verify the key policy permits `events.amazonaws.com` as a service
  principal with `kms:Decrypt` and `kms:GenerateDataKey*`. A key that
  does not allow EventBridge will cause PutEvents to fail silently.

- Prefer additive changes (add a Deny statement, add a condition) over
  destructive changes (remove a statement) — additive changes are
  reversible.

- For PUBLIC_BUS findings (wildcard/cross-account PutEvents), treat as
  incident-response. Audit CloudTrail for `events:PutEvents` from
  unexpected principals during the exposure window. Identify rules that
  could have been triggered by injected events and check downstream
  targets for anomalous invocations.

## Remediation guidance

### For PUBLIC_BUS — wildcard or cross-account event injection (Steps 5a-5c)

1. Replace `Principal: "*"` with specific account/role ARNs. If
   cross-account PutEvents is required, use `aws:PrincipalOrgID` or
   `aws:SourceAccount` conditions:
   ```bash
   aws events put-permission --event-bus-name <bus> \
     --action events:PutEvents \
     --principal arn:aws:iam::222222222222:role/app-publisher \
     --statement-id CrossAccountScoped \
     --condition '{"Type":"StringEquals","Key":"aws:SourceAccount","Value":"222222222222"}'
   ```
2. Remove the wildcard statement:
   ```bash
   aws events remove-permission --event-bus-name <bus> --statement-id OpenIngest
   ```
3. Assume breach — audit CloudTrail for `events:PutEvents` from
   unexpected principals. Check downstream targets for anomalous
   invocations triggered by injected events.

### For NO_DLQ — missing dead-letter queue (Step 6)

1. Create a dedicated SQS DLQ:
   ```bash
   aws sqs create-queue --queue-name <bus>-dlq
   ```
2. Attach to each target via `put-targets` with `DeadLetterConfig`:
   ```bash
   aws events put-targets --rule <rule> --event-bus-name <bus> \
     --targets '[{"Id":"<target-id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<acct>:<bus>-dlq"}}]'
   ```
3. Set an alarm on DLQ depth (ApproximateNumberOfMessagesVisible > 0).

### For NO_ENCRYPTION — no customer-managed KMS key (Step 7)

1. Associate a CMK:
   ```bash
   aws events update-event-bus --name <bus> \
     --kms-key-identifier arn:aws:kms:<region>:<account>:key/<key-id>
   ```
2. Verify the key policy allows `events.amazonaws.com` service principal
   with `kms:Decrypt` and `kms:GenerateDataKey*`.
3. Enable rotation on the CMK and audit the key policy (route to
   kms-key-policy-auditor).

### For CONFIG_GAP — missing archive or schema discovery (Step 8)

1. Create an archive for replay capability:
   ```bash
   aws events create-archive --archive-name <bus>-archive \
     --event-source-name <bus> --event-pattern '{"replay-name":"*"}' \
     --retention 30
   ```
2. Enable schema discovery:
   ```bash
   aws schemas create-registry --registry-name <bus>-schemas \
     --description "Auto-discovered schemas for <bus>"
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit when rules or targets are added.
3. Verify DLQ alarms are wired to an operational response channel.

## Recent AWS features (2024-2026)

- **EventBridge global endpoints GA (2024):** Global endpoints provide automatic failover for event buses across regions. Auditors should verify that the global endpoint's secondary bus has equivalent security configuration (bus policy, KMS encryption, DLQ) as the primary.
- **EventBridge Scheduler (2024-2025):** EventBridge Scheduler is a separate service for managed scheduled events. Auditors should verify that scheduler targets have scoped IAM roles and that the schedule does not inadvertently trigger public endpoints.
- **Schema registry updates (2024):** Enhanced schema registry with OpenAPI and JSON Schema support. No new audit-surface fields.
- **Cross-account event bus enhancements (2024):** Improved cross-account PutEvents support with resource-based policy evaluation. Auditors should verify that cross-account bus policies include `aws:SourceAccount` conditions.

## Domain

AWS CloudOps / EventBridge Security & App Integration.

## AWS documentation

- **Amazon EventBridge User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- **EventBridge Security** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-security.html
- **EventBridge API Reference** — https://docs.aws.amazon.com/eventbridge/latest/api-reference/
- **EventBridge CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/events/
- **EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
