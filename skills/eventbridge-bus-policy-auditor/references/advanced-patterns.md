# Advanced Patterns

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Step 0: Expert knowledge — non-obvious EventBridge behaviors (moved from SKILL.md)

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

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **EventBridge global endpoints GA (2024):** Global endpoints provide automatic failover for event buses across regions. Auditors should verify that the global endpoint's secondary bus has equivalent security configuration (bus policy, KMS encryption, DLQ) as the primary.
- **EventBridge Scheduler (2024-2025):** EventBridge Scheduler is a separate service for managed scheduled events. Auditors should verify that scheduler targets have scoped IAM roles and that the schedule does not inadvertently trigger public endpoints.
- **Schema registry updates (2024):** Enhanced schema registry with OpenAPI and JSON Schema support. No new audit-surface fields.
- **Cross-account event bus enhancements (2024):** Improved cross-account PutEvents support with resource-based policy evaluation. Auditors should verify that cross-account bus policies include `aws:SourceAccount` conditions.
