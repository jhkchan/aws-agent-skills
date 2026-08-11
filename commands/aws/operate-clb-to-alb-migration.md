---
description: Operate Classic Load Balancer (CLB) to Application Load Balancer (ALB) migrations — feature-parity assessment, target group creation, listener/rules migration, deregistration delay tuning, SSL certificate migration, weighted DNS cutover, and rollback — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "migrate CLB to ALB"
  - "Classic Load Balancer migration"
  - "CLB to ALB cutover"
  - "connection draining to deregistration delay"
  - "proxy protocol to X-Forwarded-For"
  - "ALB target group from CLB"
  - "ALB listener rule migration"
  - "Route 53 weighted routing cutover"
  - "ALB Lambda target migration"
  - "ALB OIDC authentication"
  - "WAF on ALB after migration"
  - "ALB rollback to CLB"
  - "ALB SSL certificate migration"
  - "ELBv2 create-listener from CLB"
  - "CLB feature parity"
routes_to: clb-to-alb-migration-operator
---

# /aws:operate-clb-to-alb-migration

Activate the `clb-to-alb-migration-operator` skill and plan/execute a
Classic Load Balancer to Application Load Balancer migration with
deterministic pre-checks, CONFIRM gate, and post-verification.

## What it does

Reads a Classic Load Balancer configuration (`elb describe-load-
balancers`) plus the intended migration operation and applies the
priority-ordered pre-check sequence:

1. Pre-flight CLB metadata gate — short-circuit single-AZ CLBs,
   unresolvable SSL certs, TCP/SSL passthrough listeners (route to
   NLB), Proxy Protocol backends (must read X-Forwarded-For).
2. Pre-check gate — BLOCKED if any check fails (TCP listener without
   NLB plan, Proxy Protocol backend incompatible with ALB, SSL cert
   not in ISSUED state, target SG not allowing ALB SG on target port,
   health check path not returning 200).
3. READY — emit the exact CLI sequence (create-load-balancer,
   create-target-group with stickiness + deregistration delay,
   create-listener with cert + SSL policy, create-rule for path/host
   routing, Route 53 weighted change-resource-record-sets) and the
   CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   verify target health and ALB 200 on canary.
5. Post-verification — describe-target-health shows healthy, ALB
   access logs show 2xx, CloudWatch 5xx within baseline, Route 53
   weights match intent. COMPLETED only if ALL post-verification
   checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <plan-migration | create-target-groups | migrate-listeners | cutover-dns | rollback | verify-cutover>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <clb-name> -> <alb-name-or-"planned"> (account <account>, region <region>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <verification command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <feature-parity deltas, cutover phase, rollback window, caveats>
```

## When to invoke

Paste a CLB configuration plus the intended operation, or just
describe the scenario and ask any of:

- "migrate this Classic Load Balancer to an ALB"
- "the CLB has a TCP listener — can it move to ALB?"
- "the backend uses Proxy Protocol — will ALB break it?"
- "create target groups from the CLB backends"
- "migrate listeners and add path-based routing"
- "tune deregistration delay to match CLB connection draining"
- "cut over DNS with weighted Route 53 routing"
- "roll back the ALB migration to the CLB"
- "verify the cutover is complete"
- "does ALB support OIDC / WAF / Lambda targets?"

A bare CLB name or DNS + any migration verb also routes here via the
orchestrator.

## Inputs

- CLB configuration (`elb describe-load-balancers` JSON): `Scheme`,
  `Subnets`, `SecurityGroups`, `ListenerDescriptions` (protocol, port,
  instance protocol, instance port, SSLCertificateId), `HealthCheck`,
  `Policies` (sticky, Proxy Protocol), `Attributes`
  (ConnectionDraining, CrossZoneLoadBalancing, AccessLog,
  ConnectionSettings).
- CLB tags (`elb describe-tags`) — replicate onto the ALB.
- ACM certificate status (`acm describe-certificate`) — verify ISSUED.
- Subnet AZ spread (`ec2 describe-subnets`).
- Target security groups (`ec2 describe-security-groups`) — verify
  they allow the planned ALB SG.
- Route 53 record sets (`route53 list-resource-record-sets`) —
  identify the CLB alias for cutover.
- CloudWatch baselines (`AWS/ELB` RequestCount, 5xx) for weighted
  cutover gates.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI command sequence (create-load-balancer,
  create-target-group, create-listener, create-rule, Route 53
  change-resource-record-sets), the feature-parity matrix, and the
  CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, including
  describe-target-health all healthy, ALB 5xx within baseline, Route 53
  weights match intent, no client-reported errors.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., route TCP listener to NLB, reconfigure Proxy Protocol backend
  to read X-Forwarded-For, re-issue IAM cert via ACM, update target SG
  to allow ALB SG).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for CLB-to-ALB migration).
- `/aws:troubleshoot-alb-5xx` for post-cutover 5xx triage on the new
  ALB.
- `/aws:audit-cloudfront-distribution` if a CloudFront distribution
  fronts the CLB/ALB and the origin needs updating at cutover.
