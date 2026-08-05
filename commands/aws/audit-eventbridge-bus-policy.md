---
description: Audit an EventBridge event bus for public event-injection exposure, missing dead-letter queues, absent customer-managed KMS encryption, and archive gaps.
nl_triggers:
  - "audit this event bridge bus"
  - "check eventbridge bus policy"
  - "event injection risk"
  - "is my event bus public"
  - "event bus cross-account"
  - "Principal star eventbridge"
  - "missing DLQ on rule"
  - "is event bridge encrypted"
  - "event bridge archive gap"
  - "dead-letter queue check"
  - "eventbridge wildcard permissions"
  - "hardening event bridge bus"
routes_to: eventbridge-bus-policy-auditor
---

# /aws:audit-eventbridge-bus-policy

Activate the `eventbridge-bus-policy-auditor` skill and audit one or more
EventBridge event bus configurations (bus policy + metadata + rules +
targets + archive) for security exposure.

## What it does

Reads an event bus policy document plus bus metadata (KmsKeyIdentifier),
rule/target configs (DeadLetterConfig), and archive status, then applies
the ordered classification logic:

1. Bus type — default bus (service-event delivery) vs custom bus.
2. Principal scope — WILDCARD_PRINCIPAL vs CROSS_ACCOUNT vs
   SERVICE_PRINCIPAL vs SAME_ACCOUNT.
3. Action danger — INJECT (PutEvents — blast-radius multiplier) vs
   ADMIN (PutRule, PutPermission) vs READ.
4. Condition strength — aws:PrincipalOrgID / aws:SourceAccount are
   STRONG; aws:SourceIp 0.0.0.0/0 and events:source (not a real
   condition key) are WEAK.
5. Policy severity matrix — PUBLIC_BUS determination for unrestricted
   injection.
6. Dead-letter queue — per-TARGET DeadLetterConfig check (not per-rule).
7. KMS encryption — KmsKeyIdentifier absent = AWS-owned key.
8. Archive/enrichment — archive for replay, schema discovery.
9. Aggregation — worst finding wins (PUBLIC_BUS > NO_DLQ >
   NO_ENCRYPTION > CONFIG_GAP > OK).

Emits a deterministic VERDICT per bus:

```text
BUS: <bus-name>
VERDICT: PUBLIC_BUS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PUBLIC_BUS] <finding description (Step Na)>
  - [NO_DLQ] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an event bus policy and metadata and ask any of:

- "audit this event bridge bus"
- "is my event bus public?"
- "check for event injection risk"
- "are dead-letter queues configured?"
- "is event bridge encrypted with a CMK?"
- "does this bus have an archive?"

A bare bus name/ARN + any audit verb ("audit this bus", "check bus
policy") also routes here via the orchestrator.

## Inputs

- An event bus policy document (JSON), pasted inline or referenced by
  file path.
- Bus metadata: KmsKeyIdentifier (absent = AWS-owned key), bus name/ARN.
- Rules: name, EventPattern, targets with DeadLetterConfig status.
- Archive: present (with retention) or absent.

## Outputs

- One VERDICT block per bus (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: replace wildcard principals, add conditions,
  attach DLQs, associate CMK, create archive.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for EventBridge security).
- `/aws:audit-kms-key-policy` for auditing the customer-managed KMS key
  referenced by `KmsKeyIdentifier`.
