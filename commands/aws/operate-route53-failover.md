---
description: Operate Route 53 DNS failover operations — planned weighted/failover-routing failover, emergency failover with TTL lowering, failback to primary, health check create/update, diagnose-failover, update-routing — with deterministic pre-checks, CONFIRM gate, and post-verification via test-dns-answer.
nl_triggers:
  - "failover DNS"
  - "switch Route 53 primary secondary"
  - "planned failover weighted"
  - "emergency failover"
  - "failback to primary"
  - "Route 53 health check"
  - "DNS failover did not switch"
  - "traffic not failing over"
  - "multivalue answer routing"
  - "weighted routing canary"
  - "geolocation DR routing"
  - "cross-account Route 53 hosted zone"
  - "TTL for failover"
  - "test-dns-answer"
  - "create health check"
  - "calculated health check"
  - "insulated health check"
routes_to: route53-failover-operator
---

# /aws:operate-route53-failover

Activate the `route53-failover-operator` skill and plan/execute a Route
53 DNS failover operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads a hosted zone + record set configuration plus the intended
operation and applies the priority-ordered pre-check sequence:

1. Pre-flight zone + record set gate — short-circuit deleted zones,
   wrong-routing-policy records, cross-account IAM gaps.
2. Pre-check gate — BLOCKED if any check fails (health check
   unhealthy with no working secondary, secondary unreachable, TTL too
   high for emergency failover, cross-account IAM denied, both records
   unhealthy).
3. READY — emit the exact change-resource-record-sets JSON batch with
   all fields populated, the expected DNS propagation time (TTL-
   bounded), and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the
   change-batch, poll `get-change` until INSYNC.
5. Post-verification — `test-dns-answer` returns the new primary IP,
   `dig` from multiple resolvers confirms, application metrics show
   the traffic shift. COMPLETED only if ALL post-verification checks
   pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <planned-failover | emergency-failover | failback | create-health-check | update-health-check | diagnose-failover | update-routing>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <fqdn> (hosted zone: <id>, routing policy: <policy>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <change-batch JSON with all fields populated>
  2. <poll / monitor command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <TTL, propagation, monitoring, caveats>
```

## When to invoke

Paste a hosted zone + record set configuration plus the intended
operation, or just describe the scenario and ask any of:

- "failover to the secondary region"
- "shift traffic from blue to green weighted 100/0"
- "the primary is down — emergency failover"
- "failback to primary after the outage"
- "Route 53 didn't switch traffic — diagnose"
- "create a health check on /health endpoint"
- "set up a calculated health check with CloudWatch alarm"
- "lower TTL to 60 for faster failover"
- "configure multivalue answer routing"

A bare FQDN + any failover verb also routes here via the orchestrator.

## Inputs

- Hosted zone (`list-hosted-zones-by-name`) and record sets
  (`list-resource-record-sets`): `RoutingPolicy`, `TTL`, `Failover`,
  `Weight`, `SetIdentifier`, `HealthCheckId`, `ResourceRecords`.
- Health check configuration (`get-health-check` and
  `get-health-check-status`): Type, IPAddress, Port, ResourcePath,
  SearchString, RequestInterval, FailureThreshold,
  HealthCheckObservations.
- `test-dns-answer` output from multiple resolvers.
- CloudWatch alarm wiring on `AWS/Route53` `HealthCheckStatus`.
- For cross-account: the operator's role ARN and the zone-owning
  account's IAM/RAM grant.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact `change-resource-record-sets` change-batch
  JSON, expected propagation time, expected DNS answer post-change,
  and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, including
  `test-dns-answer` from multiple resolvers and the application
  metric verification window.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., lower TTL to 60s, add cross-account IAM grant, restore the
  secondary endpoint before failover).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for Route 53 DNS failover).
- `/aws:audit-route53-records` for the audit-side counterpart —
  auditing record-set posture across many zones without changing
  state.
- `/aws:deploy-cloudfront-distribution` for the deploy-side
  counterpart (CloudFront origins often pair with Route 53 failover).
