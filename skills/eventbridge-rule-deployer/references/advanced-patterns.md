# Advanced Patterns

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Mindset (moved from SKILL.md)

**One-line takeaway:** an EventBridge rule is a **stateless filter
plus a fan-out dispatcher** — it matches events on a bus (or fires
on a schedule) and dispatches to up to 5 targets. Correct deployment
is three independent gates: pattern (does the right event match?),
target wiring (does the right consumer get invoked with the right
payload?), and resilience (DLQ + retry + idempotency). Skip any one
and the workflow is silently broken in production.

- **Pattern vs Schedule is the first fork.** A pattern rule listens
  on a bus for matching events; a schedule rule fires on a cron/rate.
  They share the `put-rule` API but share no semantics. Picking the
  wrong type produces a rule that never fires (schedule when events
  are expected) or fires on every event (pattern when a schedule is
  intended).
- **The target is where most production bugs live.** A mis-scoped
  invocation permission, a missing DLQ, an unconfigured input
  transformer, or a target ARN from the wrong account each produces
  silent non-delivery. The rule looks healthy; the consumer never
  runs.
- **At-least-once delivery is the implicit contract.** EventBridge
  may deliver the same event multiple times (retry, replay, regional
  failover). Every target consumer MUST be idempotent. A rule
  deployment that omits an idempotency note for the consumer is
  incomplete.

## Step 0: Expert knowledge — non-obvious EventBridge behaviors (moved from SKILL.md)

These behaviours change a deployment plan if ignored. Each has caused
production silent-non-delivery incidents:

- **`PutEvents` is the only event ingestion API.** AWS services call
  it implicitly; applications must call it explicitly. The bus
  policy controls who can call `PutEvents` — same-account same-bus
  is implicit, cross-account requires a resource policy.

- **`EventPattern` is JSONPath-like, not full JSONPath.** It supports
  exact match, prefix, suffix, contains, equals-ignore-case, numeric
  ranges, CIDR matching, exists, and anything-but. It does NOT
  support arbitrary JSONPath expressions like `$..user`. Complex
  filters must be done in the consumer.

- **`InputTransformer` is per-target and replaces the payload.** A
  rule can have up to 5 targets, each with its own transformer. The
  original event payload is NOT passed to the target unless the
  transformer explicitly maps it via `InputPathsMap` +
  `InputTemplate`.

- **`put-targets` accepts a non-existent DLQ ARN silently.** The
  first failed delivery will then fail to write to the DLQ — double
  silent failure. Always verify the DLQ exists with
  `aws sqs get-queue-url` before `put-targets`.

- **`test-event-pattern` is the deployment test fixture.** It
  validates a pattern against a sample event WITHOUT creating the
  rule. Always run it before `put-rule` to confirm the match.

- **Schedule expression format differs by AWS service.** EventBridge
  rules use AWS cron with required `?` in the day-of-week or
  day-of-month field (`cron(0 2 * * ? *)`). EventBridge Scheduler
  uses standard cron with optional `?`. Mixing them produces a
  validation error.

- **Same-bus same-account PutEvents does not require a bus policy.**
  Same-account access is implicit. The bus policy gates
  cross-account and service-principal delegation only.

- **Cross-account rules are bus-policy + target-ACL problems.** The
  producing account needs `events:PutEvents` permission on the
  receiving bus (via bus resource policy). The receiving rule's
  target must trust the producing account if it is in yet another
  account.

- **`PutEvents` accepts up to 10 events per call, 256 KB per event,
  2 MB total.** Events over 256 KB must be parked in S3 and
  referenced by URI in the event detail. Application publishers must
  batch and respect size caps.

- **API destinations rate-limit per connection.** A target API
  destination has a per-connection rate limit (default 300 TPS).
  Sustained excess is buffered up to the
  `InvocationRateLimitPerSec` cap; sustained overage is dropped to
  DLQ.

- **Archives replay to ALL matching rules — including rules created
  AFTER the original events.** Replay can cause unexpected duplicate
  processing. Pause new rules before replaying.

- **Rule quotas: 300 rules per bus, 5 targets per rule.** A
  high-volume workflow with many filtered sub-routes hits the cap.
  Fan out to SQS for finer-grained per-consumer filtering.

- **Scheduler has a 1M-schedule quota; rule-based scheduling has a
  300-rule-per-bus quota.** Beyond ~300 schedules, use Scheduler.

- **Global endpoints replicate EVENTS, not rules.** Both regional
  buses must have equivalent rules and targets. A failover to a bus
  without matching rules is silent event loss.

- **Schema Registry auto-discovery captures schemas only on the
  default bus by default.** Custom-bus schema discovery must be
  explicitly enabled via `discoverers` API.

## Step 7: Custom event bus vs default (moved from SKILL.md)

| Bus type | Use when | Example events |
|---|---|---|
| **default** | AWS service events | `aws.ec2`, `aws.guardduty`, `aws.securityhub` |
| **custom** | Application events | `my.app.order`, `my.app.user` |
| **partner** | SaaS partner events | `aws.partner/datadog.com/*`, `aws.partner/stripe.com/*` |

Create a custom bus:

```bash
aws events create-event-bus \
  --name app-events \
  --event-source-name "" \
  --tags '[{"Key":"Owner","Value":"app-team"},{"Key":"Environment","Value":"prod"}]'
```

Naming conventions:
- Lowercase, hyphen-separated: `app-events`, `order-bus`, `audit-events`
- Avoid `default` (reserved), `aws.*` (reserved for AWS)
- Prefix with team or domain for clarity: `payments-events`, `secops-events`

Cross-bus routing is not supported — a rule on the default bus
cannot match events on a custom bus. Use a Lambda on the default bus
that re-publishes to the custom bus if cross-bus routing is required.

## Appendix B — Common AWS event sources (moved from SKILL.md)

| Source | Detail-type | Common filter | Typical target |
|---|---|---|---|
| `aws.ec2` | `EC2 Instance State-change Notification` | `detail.state=["running"]` | Lambda auto-tagger |
| `aws.guardduty` | `GuardDuty Finding` | `detail.severity>=7` | Lambda isolate-instance |
| `aws.securityhub` | `Security Hub Findings - Imported` | `detail.findings[].Severity.Label=["CRITICAL","HIGH"]` | Step Functions workflow |
| `aws.codebuild` | `CodeBuild Build State Change` | `detail.build-status=["FAILED"]` | SNS + Lambda notify |
| `aws.autoscaling` | `EC2 Instance Launch Successful` | — | Lambda register-to-target-group |
| `aws.s3` | `Object Created` | `detail.object.key=[{"prefix":"uploads/"}]` | Lambda trigger-processing |
| `aws.cloudwatch` | `CloudWatch Alarm State Transition` | `detail.stateName=["ALARM"]` | SNS then Lambda ack |
| `aws.signin` | `AWS Console Sign In` | `detail.eventName=["ConsoleLogin"]`, `detail.responseElements.ConsoleLogin=["Success"]` | Lambda alert on new MFA-disabled logins |
| `aws.iam` | `AWS API Call via CloudTrail` | `detail.eventName=["DeleteRole"]` | Lambda revert or alert |
| `aws.health` | `AWS Health Event` | `detail.service=["EC2"]` | SNS page on-call |

## Expert heuristic: the 5-point deployment gate (moved from SKILL.md)

Before emitting READY_TO_DEPLOY, every rule deployment plan MUST pass
these five checks. Any failure is PREREQUISITES_MISSING with a
specific citation:

1. **Pattern validates** — `test-event-pattern` returns a match on
   a known-good sample. A pattern that matches nothing in test will
   never fire in production.
2. **Target ARNs resolve** — every target ARN exists in the target
   account/region. A non-existent target produces silent non-delivery.
3. **DLQ exists with 14-day retention** — `aws sqs get-queue-url`
   returns the queue; `MessageRetentionPeriod=1209600`. Default 4-day
   retention is too short for triage.
4. **Invocation permissions granted** — Lambda targets have
   `events.amazonaws.com` in their resource policy; cross-account
   targets have the appropriate bus policy.
5. **Consumer idempotency noted** — the plan explicitly documents
   the dedup key (e.g., `detail.id`, `bucket+key+etag`,
   `build-id+status`) and the consumer's idempotency mechanism.
   EventBridge is at-least-once; a consumer without idempotency is
   a production incident waiting to happen.

If all five pass, emit READY_TO_DEPLOY. Any miss is a specific GAP.

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **EventBridge global endpoints GA (2024):** Automatic regional
  failover for event buses. Requires matching rules and targets on
  the secondary bus; verify before failover.

- **EventBridge Scheduler (2024-2025):** First-class time-based
  scheduling with per-schedule IAM roles, timezones, and one-time
  schedules. Preferred over cron-style EventBridge rules for any
  new time-based workflow.

- **EventBridge Pipes enhancements (2024):** Added support for
  self-managed Kafka, MSK, and improved enrichment (Lambda, Step
  Functions, API destination, Batch, ECS). Pipes are the standard
  path for stream/queue fan-out.

- **Schema Registry updates (2024):** OpenAPI and JSON Schema
  support. Discover schemas on custom buses explicitly — auto-
  discovery only applies to the default bus. Code bindings available
  for Java, Python, TypeScript.

- **EventBridge API destinations improvements (2024-2025):**
  Enhanced credential management for OAuth client-credentials. API
  key and basic-auth credentials still do NOT auto-rotate — monitor
  `InvocationHttpStatusCode` for stale credentials.

- **`PutEvents` batch size and EntrySize limits (2024):** Still 10
  entries per call, 256 KB per entry. Events over 256 KB must be
  parked in S3 and referenced by URI.

- **Cross-account event routing via AWS Organizations (2024):** Bus
  policies now support `aws:PrincipalOrgID` condition for
  organization-wide event routing. Simplifies multi-account
  architectures vs. enumerating each account principal.
