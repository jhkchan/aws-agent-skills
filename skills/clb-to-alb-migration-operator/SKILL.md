---
name: clb-to-alb-migration-operator
description: Operates Classic Load Balancer (CLB) to Application Load Balancer (ALB) migrations end-to-end — pre-migration feature assessment (proxy protocol vs X-Forwarded-For, sticky sessions, SSL termination, connection draining vs deregistration delay), ALB target group creation mapping each CLB backend port/protocol, listener migration with path/host-based routing, deregistration delay tuning, SSL/TLS certificate migration (ACM or IAM), DNS cutover (Route 53 weighted canary vs direct swap), rollback strategy, and latest-feature coverage (ALB with Lambda targets, ALB with OIDC via Cognito, ALB WAF). Runs deterministic pre-checks (CLB scheme matches ALB, subnet count >= 2, no TCP passthrough listener, SSL cert resolvable, health check path reachable) behind a CONFIRM gate and emits READY, BLOCKED, or COMPLETED per migration. Use when planning a CLB-to-ALB migration, validating feature parity, cutting over traffic, or rolling back.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws elbv2 describe-load-balancers, create-load-balancer, create-target-group, create-listener, create-rule, modify-target-group-attributes, describe-attributes (for CLB draining), aws elb describe-load-balancers (Classic), describe- tags, aws acm list-certificates, describe-certificates, aws route53 list-resource-record-sets...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Migrating a Classic Load Balancer to an Application Load Balancer, planning feature parity (sticky sessions, SSL termination, connection draining), creating ALB target groups that map CLB backends, migrating listeners and adding path/host-based listener rules, tuning deregistration delay to match the CLB's connection draining timeout, migrating SSL certificates from IAM/ACM to ALB listeners, performing a DNS cutover via Route 53 weighted routing (canary) or direct swap, rolling back a failed migration, or diagnosing why ALB targets are unhealthy post-cutover.
  when_not_to_use: ALB-to-NLB conversions (different feature parity; use a separate planning effort), pure 5xx triage on the existing CLB (use alb-5xx-troubleshooter-style diagnosis on CLB access logs), or cost optimization of an existing ALB (use the optimize task type). This skill drives the migration plan and cutover, not runtime triage.
  activation_triggers: migrate CLB to ALB, Classic Load Balancer migration, CLB to ALB cutover, connection draining to deregistration delay, proxy protocol to X-Forwarded-For, ALB target group from CLB, ALB listener rule migration, Route 53 weighted routing cutover, ALB Lambda target, ALB OIDC authentication, WAF on ALB, ALB rollback, ALB SSL certificate migration, ELBv2 create-listener from CLB
  invocation_schema: 'Input: either (a) a Classic Load Balancer configuration (elb describe- load-balancers output) plus the intended operation (plan-migration, create-target-groups, migrate-listeners, cutover-dns, rollback, verify-cutover), OR (b) a CLB DNS name + operation for live-account execution. Output: a deterministic OPERATION / VERDICT / TARGET / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per migration, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Classic Load Balancer, CLB, ELB, Application Load Balancer, ALB, ELBv2, migration, cutover, target group, listener rule, SSL certificate, ACM, deregistration delay, connection draining, proxy protocol, X-Forwarded-For, X-Forwarded-Proto, sticky session, L7 load balancing, Route 53 weighted routing, Lambda target, OIDC, WAF on ALB, rollback
  tags: aws, elbv2, elb, alb, clb, load-balancer, networking, migration, operate
---

# CLB-to-ALB Migration Operator

## What this skill does

Executes Classic Load Balancer to Application Load Balancer migrations
correctly and safely. Runs deterministic pre-checks before any
state-changing CLI (CLB scheme matches ALB, two-or-more subnets in
different AZs, SSL certificate ARN resolvable, target group health check
path reachable, deregistration delay tuned to match CLB connection
draining, security groups allow ALB-to-target traffic), executes the
`create-load-balancer` / `create-target-group` / `create-listener` /
`create-rule` CLI sequence behind a CONFIRM gate, and verifies the
result by confirming `describe-target-health` returns healthy targets,
the ALB responds 200 on the canary path, and Route 53 weighted routing
shifts traffic incrementally. Every migration produces a feature-parity
matrix (CLB feature -> ALB equivalent) and a rollback plan (CLB stays
provisioned; flip the Route 53 weighted record back to 100/0). The
latest-feature coverage ensures operators know about ALB Lambda targets,
ALB OIDC via Cognito, and ALB-attached WAF — capabilities CLB does not
have that may simplify the post-migration architecture.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **Mindset** | Why ALB is L7-native, the feature-parity gap, the weighted cutover | Understanding the safety model |
| **Pre-flight** | CLB metadata gate — scheme, subnets, listeners, draining, SGs | Before executing any CLI |
| **Process** | Per-operation planning: plan, target groups, listeners, cutover, rollback | When choosing which operation to run |
| **STRICT output contract** | OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **Anti-Patterns — NEVER** | Common mistakes that break migrations or strand traffic | Review before risky operations |
| **Pre-flight safety** | Capture pre-state, weighted routing, rollback guardrails | Defense-in-depth |
| **Expert heuristic** | The five non-obvious signals senior engineers check first | When the plan looks wrong |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (single-AZ subnet, SSL cert not resolvable in ACM, listener uses TCP/SSL passthrough that ALB cannot replicate without NLB, health check path 404, CLB cross-zone off when ALB requires on) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Migration step finished and post-verification passed (targets healthy, ALB 200 on canary, Route 53 weights match intent, no traffic drop in CloudWatch) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **CLB reachability** — CLB exists (`describe-load-balancers` does not
   return `NoSuchLoadBalancer`), `Scheme` matches the planned ALB
   (`internet-facing` vs `internal`).
2. **Subnet count and AZ spread** — at least two subnets in two
   different AZs for the ALB. ALB requires multi-AZ; CLB technically
   supports single-AZ (anti-pattern).
3. **Listener parity** — every CLB listener has a planned ALB listener
   or listener rule. TCP/SSL passthrough listeners (CLB `TCP` or `SSL`
   protocol) CANNOT be replicated on ALB — they require NLB. Flag and
   route to NLB planning.
4. **SSL certificate resolvability** — every HTTPS listener's
   certificate (ACM ARN or IAM ARN) is resolvable, in `ISSUED` state,
   and in the same region as the planned ALB.
5. **Deregistration delay tuning** — the CLB's `ConnectionDraining`
   timeout maps to the ALB target group attribute
   `deregistration_delay.timeout_seconds`. Default is 300s on ALB; CLB
   default is 300s. Mismatched values cause connection drops at cutover.
6. **Security group reachability** — the target security groups allow
   the ALB security group (referenced SG, not CIDR) on the target port.
   CLB-to-target traffic used the CLB SG; the ALB has a new SG that
   targets must allow.
7. **Health check path reachability** — the planned health check path
   returns 200 from at least one target. CLB health checks were often
   TCP-level; ALB health checks are HTTP/HTTPS and path-specific.
8. **DNS cutover plan clarity** — Route 53 hosted zone and the CLB's
   alias record identified; weighted routing requires a weighted policy
   rather than a latency/geolocation policy.

**Cost/time baselines (2026):**

Baselines moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when sizing or justifying the migration.

## Mindset

**One-line takeaway:** a CLB-to-ALB migration is a feature upgrade, not
a like-for-like swap. The ALB gains path/host routing, OIDC, WAF, and
Lambda targets but loses TCP/SSL passthrough (route to NLB) and Proxy
Protocol v1/v2 (replace with X-Forwarded-For / X-Forwarded-Proto).
Driven by three ALB realities:

- **ALB is L7-native.** CLB pretended to be L7 by adding HTTP header
  injection (X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Port), but
  routing decisions were based on the listener only. ALB routes on path,
  host, HTTP header, query string, source IP, and method. Migrations
  almost always gain a routing capability the application wanted but
  could not express on CLB. Surface this as a positive in the plan.

- **The Proxy Protocol gap.** CLB supported Proxy Protocol v1/v2 on TCP/
  SSL listeners to convey client IP/port to the backend. ALB does NOT
  support Proxy Protocol; it always injects `X-Forwarded-For`, `X-
  Forwarded-Proto`, `X-Forwarded-Port`, and `X-Forwarded-Host`. Backends
  that parsed Proxy Protocol binary frames will receive malformed data
  unless reconfigured. This is the #1 silent breakage in CLB-to-ALB
  migrations.

- **Cross-zone is always on.** ALB cross-zone load balancing is always
  enabled and free. CLB cross-zone was off by default and billable. A
  CLB with cross-zone off produces uneven target distribution after
  migration; the ALB spreads evenly.

## Pre-flight: CLB metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** page-size details moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before live enumeration.

**Live-account pre-flight (skip if offline plan audit):**

Full command list moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for live pre-flight (CLB metadata, tags, ACM certs, subnets, SGs, Route 53, CloudWatch baseline).

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: CLB configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws elb describe-load-balancers --load-
balancer-names <name> --output json and re-plan.`

| CLB attribute | Effect on migration |
|---|---|
| `ListenerDescriptions[].Protocol: TCP` or `SSL` | BLOCKED for ALB — ALB is HTTP/HTTPS only. Route to NLB planning. |
| `ListenerDescriptions[].Protocol: HTTP` or `HTTPS` | OK for ALB. Map to ALB listener with path/host rules. |
| `ListenerDescriptions[].SSLCertificateId: arn:aws:iam::...` (IAM cert) | Plan ACM re-issue or import. ACM-managed renewal is free. |
| `Policies: LBCookieStickinessPolicy` | Map to ALB target group `stickiness.enabled=true`, `stickiness.type=lb_cookie`, `stickiness.duration_seconds` from the CLB policy. |
| `Policies: AppCookieStickinessPolicy` | Map to ALB target group `stickiness.type=app_cookie`, `stickiness.app_cookie.cookie-name` from the CLB policy. |
| `Policies: ProxyProtocolPolicyType` | BLOCKED if the backend parses Proxy Protocol — ALB does NOT support Proxy Protocol. Backend must read `X-Forwarded-For` instead. |
| `Attributes.ConnectionDraining.enabled: true` + `timeout` | Map to target group `deregistration_delay.timeout_seconds` (same value). |
| `Attributes.CrossZoneLoadBalancing.enabled: false` | INFO — ALB is always cross-zone. Targets distribute evenly post-cutover. |
| `Attributes.AccessLog.enabled: true` + S3 bucket | Map to ALB `access_logs.s3.enabled=true`, same bucket (or new one). |
| `Attributes.ConnectionSettings.IdleTimeout: 60` | Map to ALB `idle_timeout.timeout_seconds` (same value). |
| `HealthCheck.Target: TCP:443` | INFO — CLB TCP health check becomes ALB HTTPS health check on `/`. Plan an HTTP path. |
| `HealthCheck.Target: HTTP:8080/healthz` | Direct map to ALB target group `HealthCheckPath: /healthz`, `Port: 8080`, `Matcher.HttpCode: 200`. |
| `Scheme: internal` | Plan ALB `--scheme internal`. SG should not allow 0.0.0.0/0. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious CLB/ALB behaviors

All Step 0 behaviors moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a plan touches TCP/SSL listeners, stickiness, health checks, Proxy Protocol, DNS TTL, rollback, or cross-zone.

### Step 1: plan-migration

Build the feature-parity matrix and the ALB resource plan from the CLB
metadata. This step produces no state change.

**Inputs:** `elb describe-load-balancers` JSON, target SG IDs, planned
ALB name, planned subnets, ACM cert ARNs.

**Pre-checks:**
- CLB exists and `Scheme` is captured.
- For each listener: classify HTTP/HTTPS (OK) vs TCP/SSL (BLOCKED ->
  NLB).
- For each policy: classify sticky (lb_cookie or app_cookie), Proxy
  Protocol (BLOCKED for ALB).
- For each cert: resolve in ACM (`ISSUED` state).
- For each subnet: confirm at least two AZs.

**Output:** the feature-parity matrix (CLB -> ALB), the planned ALB,
target groups, listeners, rules, and the cutover plan (weighted phases
or direct swap).

### Step 2: create-target-groups

Create one ALB target group per (port, protocol, stickiness-policy)
tuple observed in the CLB. CLB had one backend port/protocol per
listener; ALB separates the target group (the backend pool) from the
listener (the frontend).

**CLI template:**

```bash
aws elbv2 create-target-group --name tg-web-8080 \
  --protocol HTTP --port 8080 --vpc-id vpc-abc123 \
  --health-check-protocol HTTP --health-check-port 8080 \
  --health-check-path /healthz --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 --healthy-threshold-count 3 \
  --unhealthy-threshold-count 3 --matcher HttpCode 200 \
  --target-type instance --tags Key=clb-source,Value=prod-clb
```

Then set stickiness and deregistration delay:

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.duration_seconds,Value=3600 \
    Key=deregistration_delay.timeout_seconds,Value=300 \
    Key=proxy_protocol_v2.enabled,Value=false
```

Register the same instances the CLB used:

```bash
aws elbv2 register-targets \
  --target-group-arn <tg-arn> \
  --targets i-aaa i-bbb i-ccc
```

### Step 3: migrate-listeners

Create the ALB, then one listener per HTTPS port and one default rule
per target group. Add path/host-based listener rules for routing the
CLB could not do.

```bash
aws elbv2 create-load-balancer \
  --name prod-alb \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-alb-prod \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4

aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:111:certificate/abc \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --default-actions Type=forward,TargetGroupArn=<tg-arn>
```

For path-based rules the CLB lacked:

```bash
aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 10 \
  --conditions Field=path-pattern,Values=/api/* \
  --actions Type=forward,TargetGroupArn=<tg-api-arn>
```

### Step 4: cutover-dns (weighted routing canary)

Incrementally shift traffic from CLB to ALB via Route 53 weighted
records. Keep both records in the same hosted zone with the same name
(alias to CLB and alias to ALB).

```bash
# Phase 1: 5% to ALB
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Changes": [
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":95,"AliasTarget":{"HostedZoneId":"Z3DZXE0K...", "DNSName":"dualstack.prod-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}},
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"alb","Weight":5,"AliasTarget":{"HostedZoneId":"Z1P...","DNSName":"dualstack.prod-alb-456.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}}
  ]}'
```

Phases: 5% (1 hour) -> 25% (1 hour) -> 50% (2 hours) -> 100% (final).
Validate error rate and latency in CloudWatch at each phase.

### Step 5: rollback

If any phase shows degraded error rate or latency:

```bash
# Flip back to CLB immediately
aws route53 change-resource-record-sets ... Weight:100 for CLB, Weight:0 for ALB
```

The ALB stays provisioned; targets drain via
`deregistration_delay.timeout_seconds`. CLB resumes full traffic.

### Step 6: verify-cutover

After 100% shift, verify:

- `aws elbv2 describe-target-health --target-group-arn <tg-arn>` shows
  all targets `healthy`.
- ALB access logs show `target_status_code: 2xx` for the canary paths.
- CloudWatch `HTTPCode_Target_5XX_Count` is at or below CLB baseline.
- Route 53 record weights are `100` (ALB), `0` (CLB).
- DNS resolvers globally see the ALB (TTL elapsed).

## STRICT output contract

Every response MUST be a single block in this exact format. No prose
before or after. Substitute the angle-bracket placeholders.

```text
OPERATION: <plan-migration | create-target-groups | migrate-listeners | cutover-dns | rollback | verify-cutover>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <clb-name> -> <alb-name-or-"planned"> (account <account>, region <region>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <feature-parity deltas, cutover phase, rollback window, caveats>
```

### Worked example — plan-migration (HTTP/HTTPS CLB, READY)

```text
OPERATION: plan-migration
VERDICT: READY
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] CLB exists, Scheme: internet-facing
  - [PASS] Two subnets in us-east-1a, us-east-1b
  - [PASS] Listeners: HTTP:80 (redirect to HTTPS), HTTPS:443 (cert
    arn:aws:acm:us-east-1:111:certificate/abc, ISSUED)
  - [PASS] No TCP/SSL passthrough listeners (no NLB needed)
  - [PASS] Policies: LBCookieStickinessPolicy timeout=3600 -> ALB
    stickiness.type=lb_cookie, duration_seconds=3600
  - [PASS] No ProxyProtocolPolicyType detected (no X-Forwarded-For
    migration needed)
  - [PASS] ConnectionDraining timeout=300 -> deregistration_delay.
    timeout_seconds=300
  - [PASS] Target SG sg-target-web allows sg-alb-prod on tcp/8080
STEPS:
  1. CONFIRM: About to plan the ALB migration of prod-web-clb -> prod-
     web-alb in account 111111111111 region us-east-1. Plan only — no
     resources created. Proceed? (yes/no)
  2. (Plan output): ALB prod-web-alb, target group tg-web-8080,
     listener HTTPS:443 with cert abc, default action forward tg-web-
     8080, plus rule path /api/* -> tg-api-8080. Cutover: weighted
     5/25/50/100 over 4 hours. Rollback: flip Route 53 weights to
     100/0.
POST_VERIFY:
  - (pending execution)
NOTES:
  - Feature gains: path-based routing (/api/* to dedicated TG), WAF
    attachment, OIDC via Cognito if added later.
  - No feature loss: CLB had no Proxy Protocol, no TCP listeners.
  - Rollback window: keep CLB alive 72 hours post-cutover.
```

### Worked example — cutover-dns (Phase 1, 5% weighted, READY)

Full block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when executing cutover-dns Phase 1.

### Worked example — cutover-dns (BLOCKED, Proxy Protocol backend)

Full block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when a Proxy Protocol backend blocks the cutover.

### Worked example — verify-cutover (COMPLETED)

Full block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the post-cutover verification shape.

## Anti-Patterns — NEVER

- NEVER migrate a CLB TCP/SSL passthrough listener to ALB. ALB is
  HTTP/HTTPS only. A `TCP:443` CLB listener (SSL passthrough, no
  termination) must either terminate SSL at the ALB (accepting L7
  inspection and requiring the cert) or move to NLB. Silently dropping
  the listener orphans traffic.

- NEVER cutover DNS while the backend still parses Proxy Protocol. ALB
  does NOT emit Proxy Protocol frames; it injects `X-Forwarded-For` /
  `X-Forwarded-Proto` headers. A backend parsing Proxy Protocol will
  receive HTTP bytes, try to parse them as a binary frame, and return
  400/connection-reset for 100% of requests. Always check the CLB's
  `ProxyProtocolPolicyType` and the backend listener configuration
  before cutover.

- NEVER delete the CLB at cutover. The CLB is the rollback target. Keep
  it provisioned for at least 24-72 hours post-cutover. Rollback is a
  one-line Route 53 weight flip (100/0); CLB deletion is irreversible
  and removes the rollback path.

- NEVER assume CLB and ALB sticky-session cookies are interchangeable.
  CLB `LBCookieStickinessPolicy` and ALB `stickiness.type=lb_cookie`
  both generate an `AWSELB` cookie, but the ALB cookie is per-target-
  group and the duration semantics differ when the application also
  sets cookies. Test stickiness post-cutover with a real session.

- NEVER do a direct DNS swap on a high-traffic workload without weighted
  canary. The ALB/CLB DNS TTL is 60s, but client-side resolvers and
  application-level connection pools cache longer. A direct swap can
  route half the traffic to an ALB with a misconfigured target group
  before monitoring catches it. Use 5/25/50/100 weighted phases with
  validation at each step.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-load-balancer`, `create-target-group`, `create-listener`,
  `create-rule`, `modify-target-group-attributes`, `register-targets`,
  Route 53 `change-resource-record-sets`), emit:
  `CONFIRM: About to <operation> on <resource> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.

- **Capture pre-state for audit.** Before any migration step:
  `aws elb describe-load-balancers --load-balancer-names <clb> --output
  json > /tmp/<clb>-pre-$(date +%s).json` AND `aws route53 list-resource-
  record-sets --hosted-zone-id <zone> --output json > /tmp/<zone>-pre-
  $(date +%s).json`. These captures are critical for rollback
  diagnostics and compliance evidence.

- **Verify the ALB SG is distinct from the CLB SG.** Reusing the CLB's
  SG on the ALB couples the two and makes rollback messy. Create a
  dedicated `sg-alb-prod` with the same ingress rules; update target
  SGs to allow `sg-alb-prod`.

- **Verify target SGs allow the new ALB SG.** A target SG that allowed
  the CLB SG will not allow the ALB SG until updated. This is the most
  common post-cutover 502/503 cause.

- **Verify Route 53 hosted zone and record set.** The CLB alias record
  must be identified before cutover. Weighted routing requires the
  record to have `Weight` and `SetIdentifier`; a plain alias cannot be
  weighted incrementally.

- **Prefer additive changes over destructive ones.** Creating an ALB,
  target groups, and listeners is safe and reversible. Deleting the CLB
  or removing the Route 53 weighted record is consequential — confirm
  intent explicitly.

## Expert heuristic — the top 5 non-obvious signals

All five signals moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the plan looks too clean.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for 2024-2026 ALB feature coverage.

## References (load on demand)

- [references/feature-parity-matrix.md](references/feature-parity-matrix.md) — CLB feature to ALB equivalent mapping.
- [references/cutover-and-rollback-procedures.md](references/cutover-and-rollback-procedures.md) — weighted cutover phases, direct swap, rollback, cleanup.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, cost baselines, top-5 heuristic, 2024-2026 features.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pagination rules and live-account pre-flight commands.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (cutover Phase 1, BLOCKED, verify-cutover COMPLETED).

## Domain

AWS CloudOps / Classic Load Balancer to Application Load Balancer
Migration, L7 Modernization, and DNS Cutover Operations.

## AWS documentation

- **Migrate from Classic Load Balancer to Application Load Balancer** — https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/migrate-clb.html
- **Application Load Balancer features** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html
- **Target groups** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- **Listener rules** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-update-rules.html
- **Sticky sessions** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/sticky-sessions.html
- **Deregistration delay** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#deregistration-delay
- **ALB with Lambda targets** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html
- **Authenticate users on ALB (OIDC/Cognito)** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html
- **Route 53 weighted routing** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html
- **ACM certificates** — https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html
