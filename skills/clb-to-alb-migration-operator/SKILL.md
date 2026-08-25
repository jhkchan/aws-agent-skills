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

- ALB: $0.0225/hour + $0.008 per LCU-hour (dimensioned on connections,
  bytes, rule evaluations). CLB is a flat hourly — ALB usually cheaper
  for L7 workloads.
- ALB target groups: free. Route 53 weighted routing: $0.50/million
  queries (first billion free).
- ACM certificates: free if issued via ACM. Cross-zone: ALB always on
  and free; CLB was billable.
- WAF on ALB: $5/rule/month + $1/million requests. ALB Lambda target
  invocations: billed as Lambda (no extra ALB fee).

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

**Pagination:** `elb describe-load-balancers` paginates at 400/page —
drain `--marker`/`--next-marker`. `elbv2 describe-target-groups`
paginates at 400/page. `route53 list-resource-record-sets` paginates at
100/page (use the `--hosted-zone-id`).

**Live-account pre-flight (skip if offline plan audit):**

1. `aws elb describe-load-balancers --load-balancer-names <clb-name>
   --output json` — capture `Scheme`, `Subnets`, `SecurityGroups`,
   `ListenerDescriptions` (protocol, port, SSLCertificateId),
   `HealthCheck`, `Policies` (sticky, Proxy Protocol), `Attributes`
   (ConnectionDraining, CrossZoneLoadBalancing, AccessLog,
   ConnectionSettings).
2. `aws elb describe-tags --load-balancer-names <clb-name>` — capture
   tags for replicating onto the ALB (`create-tags`).
3. `aws elbv2 describe-load-balancers` (filter by name to confirm the
   ALB doesn't already exist with the planned name).
4. `aws acm list-certificates --certificate-statuses ISSUED --output
   json` — verify each CLB SSL cert ARN resolves to an ACM cert in
   `ISSUED` state, same region. If the cert is IAM-uploaded
   (`arn:aws:iam::...:server-certificate/...`), plan to import or
   re-issue via ACM (ACM-managed renewal is free; IAM cert renewal is
   manual).
5. `aws ec2 describe-subnets --subnet-ids <subnet-1> <subnet-2>` —
   verify AZ spread.
6. `aws ec2 describe-security-groups --group-ids <target-sg>` — verify
   the target SG allows the ALB SG (planned) on the target port.
7. `aws route53 list-resource-record-sets --hosted-zone-id <zone-id>` —
   capture the CLB alias record (alias or CNAME) for cutover planning.
8. `aws cloudwatch get-metric-statistics --namespace AWS/ELB --metric-
   name RequestCount --dimensions Name=LoadBalancerName,Value=<clb>
   --start-time ... --end-time ...` — baseline traffic volume for
   weighted-cutover increments.

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

These behaviors are easy to misjudge without migration experience. Each
changes a plan if ignored:

- **TCP/SSL listeners cannot move to ALB.** ALB supports HTTP and HTTPS
  only. A CLB with a `TCP:443` listener (SSL passthrough) must either
  terminate SSL at the ALB (requires the cert and accepting L7
  inspection) or migrate to an NLB. The skill flags this and routes the
  listener to NLB planning — do NOT silently drop the listener.

- **Sticky session semantics differ.** CLB `LBCookieStickinessPolicy`
  generates a load-balancer-generated cookie. ALB `stickiness.type=lb_
  cookie` does the same with `AWSELB` cookie. CLB `AppCookieStickiness
  Policy` honors an application cookie name. ALB `stickiness.type=app_
  cookie` does the same. The names look equivalent but the cookie
  lifetime semantics differ: CLB's app-cookie stickiness refreshed the
  expiration on every response; ALB's `app_cookie` does too, but the
  `duration_seconds` is a fallback only if the application does not set
  the cookie. Test stickiness post-cutover.

- **Health check semantics differ.** CLB health check `Target: HTTP:8080
  /healthz` used the `HTTP:` prefix and combined port + path. ALB
  separates them: `HealthCheckPort: 8080`, `HealthCheckPath: /healthz`,
  `HealthCheckProtocol: HTTP`. The matcher is also stricter on ALB —
  `Matcher.HttpCode: 200` matches only 200 by default; CLB matched 200
  by default. Mismatched matchers cause post-cutover unhealthy targets
  even though the application is fine.

- **Proxy Protocol is the silent killer.** If the backend application
  parses the Proxy Protocol binary frame (common for gaming, IoT, and
  legacy Go services using `ProxyProto` libraries), ALB will break it
  silently — ALB injects `X-Forwarded-*` headers but no Proxy Protocol
  frame. The first symptom is "all requests 400 Bad Request" or
  "connection reset" because the backend tries to parse HTTP as a Proxy
  Protocol frame. Always check the CLB's `ProxyProtocolPolicyType` and
  inspect the backend's listener configuration before cutover.

- **DNS cutover is not instant.** Clients cache the CLB DNS name's
  underlying IP for the TTL (default 60s). Weighted routing cutover
  (5%/25%/50%/100% over hours) is the safe path for high-traffic
  workloads. Direct swap is safe for low-traffic internal services.

- **The CLB stays alive during rollback.** Do NOT delete the CLB at
  cutover. Keep it provisioned for the rollback window (typically
  24-72 hours). Rollback = flip the Route 53 weighted record back to
  100/0 (CLB/ALB). Deleting the CLB prematurely is irreversible.

- **Cross-zone on ALB changes distribution.** A CLB with cross-zone off
  distributes per-AZ; ALB always cross-zone spreads evenly across all
  targets. If any target is sized for AZ-only load, it may be
  overwhelmed by ALB's even distribution.

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

```text
OPERATION: cutover-dns
VERDICT: READY
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] ALB exists, State: active
  - [PASS] All targets healthy in tg-web-8080 (3/3 healthy)
  - [PASS] ALB responds 200 on https://prod-web-alb-.../healthz from
    a canary client
  - [PASS] Route 53 hosted zone Z111 has app.example.com A record
    aliasing CLB (weight 100 implied)
  - [PASS] CloudWatch baseline: RequestCount ~5000/min, 5xx ~0
STEPS:
  1. CONFIRM: About to shift app.example.com to 95% CLB / 5% ALB via
     Route 53 weighted routing. This routes ~250 req/min to the ALB.
     Proceed? (yes/no)
  2. aws route53 change-resource-record-sets --hosted-zone-id Z111
     --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":
     {"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":95,
     "AliasTarget":{"HostedZoneId":"Z3DZXE0K...","DNSName":"dualstack.prod-
     web-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}},
     {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.",
     "Type":"A","SetIdentifier":"alb","Weight":5,"AliasTarget":{...}}]}'
  3. Monitor 15 minutes: CloudWatch HTTPCode_Target_5XX_Count on ALB;
     if > baseline+10%, run rollback (Step 5 of Process).
POST_VERIFY:
  - (pending execution)
NOTES:
  - TTL 60s — clients pick up the new weight within ~60s.
  - Next phase (25% ALB) after 1 hour at 5% with no regression.
  - Rollback: UPSERT weights to 100/0 (CLB/ALB). Takes effect in 60s.
```

### Worked example — cutover-dns (BLOCKED, Proxy Protocol backend)

```text
OPERATION: cutover-dns
VERDICT: BLOCKED
TARGET: prod-game-clb -> prod-game-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] ALB exists, State: active
  - [FAIL] CLB Policy ProxyProtocolPolicyType enabled on backend port
    4242 — the Go backend parses Proxy Protocol v2 frames. ALB does NOT
    emit Proxy Protocol; the backend will receive HTTP bytes and try to
    parse them as a Proxy Protocol header, producing 400/connection
    reset for 100% of requests.
STEPS: (none — backend incompatible)
POST_VERIFY: (none)
NOTES:
  - Root cause: ALB cannot emit Proxy Protocol. The backend must be
    reconfigured to read X-Forwarded-For / X-Forwarded-Proto headers
    instead of Proxy Protocol frames.
  - Fix: (a) update the backend listener to disable Proxy Protocol
    parsing and read X-Forwarded-For, OR (b) keep this listener on an
    NLB (which supports Proxy Protocol v2) and migrate only HTTP/HTTPS
    listeners to ALB.
```

### Worked example — verify-cutover (COMPLETED)

```text
OPERATION: verify-cutover
VERDICT: COMPLETED
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Route 53 weights: ALB 100, CLB 0
  - [PASS] DNS globally resolves to ALB (TTL elapsed 24h ago)
STEPS:
  1. aws elbv2 describe-target-health --target-group-arn <tg-web-8080>
  2. aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
     --metric-name HTTPCode_Target_5XX_Count ...
  3. aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
     --metric-name TargetResponseTime ...
POST_VERIFY:
  - [PASS] describe-target-health: 3/3 targets State: healthy
  - [PASS] HTTPCode_Target_5XX_Count: 0 over last 60 minutes (CLB
    baseline was 0-2/min)
  - [PASS] TargetResponseTime p99: 85ms (CLB baseline was 90ms)
  - [PASS] ALB access logs in S3 show target_status_code 2xx for 100%
    of /api/* requests
  - [PASS] No client-reported errors in the canary dashboard
NOTES:
  - Cutover complete. Schedule CLB deletion after 72-hour observation
    window (2026-08-12).
  - Keep Route 53 weighted record at ALB:100, CLB:0 until CLB deletion,
    then remove the CLB weighted record.
  - Post-migration optimization: consider adding ALB WAF for SQLi/XSS
    protection (was not possible on CLB).
```

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

A senior migration engineer checks these five things first when a plan
looks "too clean." Each flips a READY verdict to BLOCKED if missed:

1. **Proxy Protocol on the backend listener.** Check the CLB policy list
   for `ProxyProtocolPolicyType` AND inspect the backend application's
   listener config (nginx `proxy_protocol on;`, HAProxy `accept-proxy`,
   Go `ProxyProto` library). Either side enabling it without the other
   breaks 100% of requests. ALB has no Proxy Protocol emission —
   backends must read X-Forwarded-For.

2. **TCP/SSL listeners hiding in the policy list.** A CLB named "web"
   may still have a `TCP:4242` listener for an admin protocol. The
   listener list is the source of truth, not the name. Any TCP/SSL
   listener routes to NLB planning, not ALB.

3. **IAM-uploaded certificates (not ACM).** A cert ARN starting with
   `arn:aws:iam::` is IAM-uploaded; renewal is manual and there is no
   free managed rotation. Plan to re-issue via ACM before or during
   migration so the ALB gets free managed renewal. ACM certs are free
   and auto-renew.

4. **Deregistration delay mismatch.** The CLB's `ConnectionDraining`
   timeout maps to the ALB target group's
   `deregistration_delay.timeout_seconds`. Defaults are both 300s, but a
   CLB tuned to 60s will leave the ALB at 300s — targets drain slowly
   during rollback, leaving the operator confused. Always read the CLB
   attribute and set the ALB target group to match.

5. **Cross-zone off on CLB.** A CLB with cross-zone off distributes
   per-AZ. Targets in AZ-a only serve AZ-a traffic. ALB is always
   cross-zone, so post-cutover traffic spreads evenly. If any target is
   sized for AZ-only load (smaller instances in one AZ), it may be
   overwhelmed by ALB's even distribution. Pre-scale or rebalance
   targets before cutover.

## Recent AWS features (2024-2026)

- **ALB with Lambda targets (2024 GA):** ALB can invoke Lambda
  functions as targets, with multi-value headers and request/response
  mapping. Useful for replacing CLB-backed API endpoints with serverless
  functions without an API Gateway. No Proxy Protocol; the Lambda event
  includes the original HTTP request.

- **ALB with OIDC authentication (2024 GA):** ALB can authenticate users
  via Amazon Cognito user pools or any OIDC-compliant IdP before
  forwarding to the target. This was a common reason teams added API
  Gateway in front of CLB; ALB now does it natively. Configure via
  `authenticate-cognito` or `authenticate-oidc` action in a listener
  rule.

- **WAF on ALB (2024-2026 enhancements):** AWS WAF can be attached to
  an ALB with managed rule groups (SQLi, XSS, bot control, IP reputation,
  common RuleSet). CLB had no WAF attachment. Post-migration, enable WAF
  for defense-in-depth.

- **TLS 1.3 on ALB (`ELBSecurityPolicy-TLS13-1-2-2021-06`, 2024):** ALB
  supports TLS 1.3 with forward secrecy and 0-RTT. CLB's best was TLS
  1.2. Migrating unlocks modern TLS; do not carry over the CLB's older
  policy.

- **ALB HTTP/2 and gRPC (2024):** ALB supports HTTP/2 natively and gRPC
  routing via listener rules. CLB was HTTP/1.1 only. Migrating unlocks
  multiplexed connections and gRPC-aware routing.

- **ALB weight-based target group forwarding (2025):** A listener rule
  action can forward to multiple target groups with weights (e.g., 90%
  blue / 10% green) for native blue/green deployments without Route 53.
  CLB required Route 53 weighted for the same effect.

- **Cross-zone load balancing always on (ALB, 2024-2026):** Confirmed
  always-on and free on ALB. CLB was off by default and billable. Any
  CLB with cross-zone off will see different distribution post-migration.

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
