---
name: alb-unhealthy-target-troubleshooter
description: 'Diagnoses ALB target health check failures through a ten-category diagnostic tree: health check path misconfiguration (wrong path, non-200 response), port mismatch (target port vs health check port), protocol mismatch (HTTP vs HTTPS, HTTP/1.0 vs HTTP/1.1 expectations), deregistration delay stranding targets, security group rules blocking ALB health checker IPs, Lambda target group async failures, weighted target group routing, deregistration timeout, health check threshold/interval tuning, slow start mode, and target group attributes (stickiness, proxy protocol, preserve client IP). Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and target group configuration. Live-account diagnosis uses aws elbv2 describe-target-health, aws elbv2 describe-target-groups, aws elbv2 describe-target-group-attributes, aws ec2 describe-security-groups, aws ec2 describe-network-interfaces, aws logs filter-log-events, aws cloudwatch get-metric-statistics, aws lambda get-function-configuration...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an ALB target health check failure (targets showing unhealthy or unused, health check path errors, port or protocol mismatch, deregistration delay stranding targets, security group blocking health checker IPs, Lambda target group invocation failures, weighted target group routing issues, or slow-start mode causing apparent unhealthy targets), walking a symptom to the failed config layer with verify and fix commands.
  when_not_to_use: NLB (Network Load Balancer) target health issues (use NLB-specific tooling), Route 53 health check failures (use Route 53 monitoring), Classic ELB health checks (use classic-elb tools), application code debugging of the target itself (use the application logs and a debugger), or global accelerator endpoint health (use Global Accelerator diagnostics). This skill diagnoses ALB target-health failures; it does not tune application performance or audit steady-state load balancer posture.
  activation_triggers: ALB target unhealthy, target health check failed, target health Unused, target health Draining, ALB 502 Bad Gateway, ALB 503 Service Unavailable, health check path misconfiguration, target port mismatch, health check port mismatch, protocol mismatch HTTP HTTPS, deregistration delay, deregistration timeout, security group blocking health check, ALB health checker IP, Lambda target group unhealthy, weighted target group, slow start mode, target group stickiness, proxy protocol v2, preserve client IP, connection draining, troubleshoot ALB health check
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "targets are unhealthy", "502s from the ALB"), optionally paired with the target group configuration (describe-target-groups output) and target health output, OR (b) a Target Group ARN plus ALB context for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {HEALTH_CHECK_PATH, PORT_MISMATCH, PROTOCOL_MISMATCH, SG_BLOCKING_HEALTH_CHECK, DEREGISTRATION_DELAY, HEALTH_CHECK_THRESHOLD, LAMBDA_TARGET_INTEGRATION, WEIGHTED_ROUTING, SLOW_START, CROSS_ZONE, TARGET_GROUP_ATTRIBUTE, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "ALB target group tg-prod-app shows 4 of 6 targets as

    unhealthy. Health check is configured on /health with port 80,

    but the application listens on 8080. The health check response is a

    connection refused."

    TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-app/abc123

    TargetType: instance

    HealthCheckPath: /health

    HealthCheckPort: 80

    Target Port: 8080

    Protocol: HTTP

    HealthCheckProtocol: HTTP

    Targets: 6 registered, 4 unhealthy (Reason: Target.FailedHealthChecks)'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ALB, Application Load Balancer, target health, unhealthy target, health check, target group, deregistration delay, deregistration timeout, security group, health checker IP, Lambda target group, weighted target group, stickiness, proxy protocol, preserve client IP, slow start, cross-zone, draining, troubleshooting
  tags: alb, networking, troubleshooting, target-health, elbv2, load-balancer, health-check, security-group
---

# ALB Unhealthy Target Troubleshooter

## Quick start

Symptom->layer map, first-probe rules, health-checker IP/port independence, and deregistration-is-normal notes (full bullets): [references/advanced-patterns.md](references/advanced-patterns.md). The triage table below is the condensed navigation.

## Mindset

Full mindset (target is innocent until ALB-side config is proven correct; describe-* probes before SSH): [references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

The four senior-engineer behaviours (reason codes drive order, health-check SGs are bidirectional, draining == deregistration delay, Lambda targets use invoke-based health): [references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference -- symptom triage table

| Symptom phrase / TargetHealthReason | Most likely layer | First probe |
|---|---|---|
| All targets `unhealthy`, `Target.FailedHealthChecks` | HEALTH_CHECK_PATH / PORT_MISMATCH / SG_BLOCKING_HEALTH_CHECK | `describe-target-health` + `describe-security-groups` on target SG |
| All targets `unhealthy`, `Target.ConnectionFailed` | SG_BLOCKING_HEALTH_CHECK / PORT_MISMATCH | `describe-security-groups` (ingress on health check port from ALB SG) |
| Some targets `unhealthy`, others `healthy` | CROSS_ZONE / per-target app issue | `describe-target-health` per target; check AZ of failing targets |
| Targets `Draining` for minutes | DEREGISTRATION_DELAY | `describe-target-group-attributes` (`deregistration_delay.timeout_seconds`) |
| Targets flap `healthy`/`unhealthy` | HEALTH_CHECK_THRESHOLD | Health check interval, threshold, timeout config |
| New targets `unhealthy` then `healthy` | SLOW_START | `describe-target-group-attributes` (`slow_start.duration_seconds`) |
| Targets show `Unused` | WEIGHTED_ROUTING / CROSS_ZONE | Listener rules with weighted forwarding |
| Lambda target group `unhealthy` | LAMBDA_TARGET_INTEGRATION | Lambda function invocation logs; `Target.HealthCheckProtocol` |
| ALB returns 502 even when targets healthy | PROTOCOL_MISMATCH | Listener protocol vs target group protocol comparison |
| All targets `healthy` but app still failing | Not a health check issue | Check listener rules, host-header rules, path-pattern routing |

## Pre-flight: target group state and gather-info gate

Before running symptom-specific probes, gather the canonical target
group configuration and short-circuit on states that mimic health
check failures. Misclassifying these produces hours of debugging for a
problem that is not a health check problem.

### Account-wide pre-flight commands

Account-wide pre-flight commands (describe-target-groups, -target-health, -target-group-attributes, target SGs, load balancers, listener rules, UnHealthyHostCount metrics): [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Target-health-state short-circuit

Target-health State/Reason short-circuit table (healthy, unhealthy+reason, unused, draining, initial): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the input is malformed (missing TargetGroupArn, absent symptom
description, no target health context), emit:

INSUFFICIENT_DATA re-prompt template for malformed/missing input: [references/worked-examples.md](references/worked-examples.md).

## Process -- Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation or a
pass that moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

The 13 non-obvious behaviours (health checker uses ALB node private IPs, case-sensitive path, HealthCheckPort override, Matcher 200 default, HTTPS cert not validated, per-target drain, slow-start ramp, Lambda invoke checks, weighted traffic share, cross-zone default, stickiness masking, proxy-protocol/preserve-IP SG effects, ECS grace period): [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: Symptom entry -- pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 11
(INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| All targets `unhealthy`, `Target.FailedHealthChecks` | Step 2 -- Health check path/port/protocol |
| All targets `unhealthy`, `Target.ConnectionFailed` | Step 3 -- Security group blocking |
| Some targets `unhealthy`, others `healthy` | Step 4 -- Per-target / AZ issues |
| Targets stuck in `Draining` | Step 5 -- Deregistration delay |
| Targets flap `healthy`/`unhealthy` | Step 6 -- Threshold/interval tuning |
| New targets `unhealthy` then `healthy` | Step 7 -- Slow start |
| Targets show `Unused` | Step 8 -- Weighted routing / cross-zone |
| Lambda target group `unhealthy` | Step 9 -- Lambda target integration |
| ALB returns 502 despite healthy targets | Step 10 -- Protocol mismatch |
| None of the above | Step 11 -- INSUFFICIENT_DATA |

### Step 2: Health check path, port, or protocol misconfiguration

Symptom: all targets show `unhealthy` with reason
`Target.FailedHealthChecks`. The health checker reached the target
but the response did not match the expected status code.

#### 2a: Read the health check configuration

Probe (jq projection of every HealthCheck* field): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Config-field common-mismatch table (path/port/protocol/matcher/timeout/target-protocol): [references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 2b: Verify the health check path and response

Probes (direct curl of health endpoint on target port and health check port, http_code extraction): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the direct curl returns a non-200 code, the application is not
serving the expected response. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: HEALTH_CHECK_PATH`. Fix: update the application to return 200
on the health endpoint, or update the TG `Matcher.HttpCode` to accept
the actual response code.

#### 2c: Verify the health check port

If `HealthCheckPort` is `traffic-port`, the health check uses the
target's registered port. If it is a specific number, health checks
go to that port.

Probes (ss/netstat listener check on the health check port, from the target itself): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the application is not listening on the health check port,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: PORT_MISMATCH`. Fix: either
change `HealthCheckPort` to `traffic-port` (or the correct port), or
start the application listener on the health check port.

#### 2d: Verify the protocol

Protocol mismatch logic (HTTP->HTTPS 301 vs TLS handshake failure; align HealthCheckProtocol): [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 3: Security group blocking health checker IPs

Symptom: all targets show `unhealthy` with reason
`Target.ConnectionFailed` or `Target.FailedHealthChecks` where the
failure is a TCP connection refused/timeout.

#### 3a: Identify the ALB security group and subnets

Probe (ALB SGs, AZs, VpcId, state): [references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 3b: Check the target security group ingress rules

Probe (target SG IpPermissions; must allow ALB SG on the health check port): [references/diagnostic-commands.md](references/diagnostic-commands.md).

The target SG must allow inbound on the health check port from either:
- The ALB's security group ID (recommended -- use a SG reference)
- The ALB's subnet CIDRs (acceptable)
- 0.0.0.0/0 (works but overly permissive)

If the target SG does not allow inbound from the ALB SG on the health
check port, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: SG_BLOCKING_HEALTH_CHECK`.

Fix: add an ingress rule:

Fix command (authorize-security-group-ingress UserIdGroupPairs from ALB SG): [references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 3c: Verify with ALB ENI IPs

Probe (ALB ENI private IPs via describe-network-interfaces): [references/diagnostic-commands.md](references/diagnostic-commands.md).

From the target instance, attempt a connection:

Probe (curl to the ALB ENI IP on the health check port): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If this fails, the SG or network ACL is blocking the health check.

#### 3d: Network ACL check

NACL check rule (stateless; ephemeral ports 1024-65535 both ways on ALB + target subnets): [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 4: Per-target and per-AZ issues

Symptom: some targets are `healthy` and others are `unhealthy` in the
same target group.

#### 4a: Identify the failing targets' AZs

Probe (per-target AZ + health reason projection): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If all unhealthy targets are in the same AZ, investigate that AZ:
- The ALB node in that AZ may be degraded (check AWS Health).
- A NACL or route table issue specific to that AZ's subnet.
- The instances in that AZ may be from a degraded hardware host.

#### 4b: Per-target application issue

If failing targets are spread across AZs, the issue is likely per-
instance. SSH into a failing target and verify:
- The application process is running.
- The application responds on the health endpoint.
- The application is not crash-looping.

### Step 5: Deregistration delay stranding targets

Symptom: targets show state `draining` for an extended period after
being deregistered.

Probe (deregistration_delay.timeout_seconds attribute): [references/diagnostic-commands.md](references/diagnostic-commands.md).

The `deregistration_delay.timeout_seconds` attribute controls how long
the ALB waits (default 300 seconds = 5 minutes). During this window:
- In-flight requests are allowed to complete.
- New requests are not sent to the draining target.
- The target shows state `draining`.

If the delay is set very high (e.g., 3600 seconds), targets appear
stuck. This is not a failure -- it is configured behaviour. If the
operator needs faster removal, lower the delay:

Fix command (modify-target-group-attributes for the delay): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DEREGISTRATION_DELAY`.
The targets are draining normally per the configured timeout. No fix
needed unless the operator wants faster deregistration.

### Step 6: Health check threshold and interval tuning

Symptom: targets flap between `healthy` and `unhealthy` intermittently.
The health check is borderline -- occasionally failing enough
consecutive checks to mark unhealthy, then recovering.

#### 6a: Read the threshold and interval config

Probe (interval/timeout/threshold projection): [references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 6b: Common flapping patterns

| Pattern | Cause |
|---|---|
| `HealthCheckIntervalSeconds` too short (e.g., 10s) with a slow health endpoint | The endpoint takes 8s to respond; with a 5s timeout, the check times out. |
| `UnhealthyThresholdCount` = 2 with intermittent failures | Two consecutive failures mark the target unhealthy. Raise to 3-5 for resilience against transient blips. |
| `HealthCheckTimeoutSeconds` < app response time | The health check times out before the app responds. Raise the timeout or optimise the health endpoint. |
| `HealthyThresholdCount` too high (e.g., 10) | Recovery is slow after a transient failure; targets stay unhealthy for `10 * interval` seconds. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HEALTH_CHECK_THRESHOLD`.
Fix: tune the thresholds and intervals to match the application's
response characteristics.

### Step 7: Slow start mode

Symptom: newly registered targets show `unhealthy` initially, then
transition to `healthy`, but receive little traffic for a period after.

Probe (slow_start.duration_seconds attribute): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If `slow_start.duration_seconds` is set (30-900 seconds), the ALB
gradually ramps traffic to newly-healthy targets. During the ramp:
- The target is `healthy` (passed health checks).
- Traffic fraction starts low and increases linearly.
- The target appears underutilised compared to established targets.

This is normal behaviour, not a health check failure. If the slow
start duration is longer than expected for the application's warm-up
time, reduce it.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SLOW_START`. The target
is healthy but in the slow-start ramp period. No fix needed unless
the duration is misconfigured.

### Step 8: Weighted target groups and cross-zone issues

Symptom: targets show state `unused` -- registered and healthy but
receiving no traffic.

#### 8a: Check listener rules for weighted forwarding

Probe (ForwardConfig weights per listener rule): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If `ForwardConfig.TargetGroups` has multiple entries with different
weights, traffic is split proportionally. A target group with weight
0 receives no traffic and its targets show `unused`.

#### 8b: Check cross-zone load balancing

Probe (load_balancing.cross_zone.enabled attribute): [references/diagnostic-commands.md](references/diagnostic-commands.md).

If `load_balancing.cross_zone.enabled` is `false`, each ALB node only
sends to targets in its own AZ. Targets in an AZ without an ALB node
show `unused`.

**Verdicts:**
- Weight is 0 on the target group: ROOT_CAUSE_IDENTIFIED,
  `LAYER: WEIGHTED_ROUTING`. Fix: update the listener rule weight.
- Cross-zone disabled with targets in an AZ without an ALB node:
  ROOT_CAUSE_IDENTIFIED, `LAYER: CROSS_ZONE`. Fix: enable cross-zone
  or add ALB nodes in the target AZ.

### Step 9: Lambda target group integration failures

Symptom: a target group with `TargetType: lambda` shows the target as
`unhealthy`.

For Lambda target groups:
- Health check path and port are ignored.
- The ALB sends a GET request to the Lambda function.
- The function must return a 200 status code in the response.

#### 9a: Check the Lambda function health

Probes (function State/Timeout, error log filter for timeouts and runtime exits): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Lambda failure-pattern catalog (timeout, non-200, exception, multi-value headers, unhandled GET event): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: LAMBDA_TARGET_INTEGRATION`. Fix: ensure the function returns
200 on the health check invocation, does not time out, and properly
handles the ALB event format.

### Step 10: Protocol mismatch causing 502s

Symptom: the ALB returns 502 Bad Gateway even though targets show
`healthy`.

Listener/TG protocol compatibility table and 502-when-healthy causes (keep-alive, HTTP/1.1, HTTPS-vs-HTTP mismatch): [references/target-group-attribute-reference.md](references/target-group-attribute-reference.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PROTOCOL_MISMATCH`. Fix:
align the target group protocol with the application's actual protocol.

### Step 11: INSUFFICIENT_DATA

INSUFFICIENT_DATA fallback template (probe list + the 5 context items to request): [references/worked-examples.md](references/worked-examples.md).

## Output format

```text
TARGET: <target-group-arn or name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <HEALTH_CHECK_PATH | PORT_MISMATCH | PROTOCOL_MISMATCH |
        SG_BLOCKING_HEALTH_CHECK | DEREGISTRATION_DELAY |
        HEALTH_CHECK_THRESHOLD | LAMBDA_TARGET_INTEGRATION |
        WEIGHTED_ROUTING | SLOW_START | CROSS_ZONE |
        TARGET_GROUP_ATTRIBUTE | UNKNOWN>
EVIDENCE:
  - <observed symptom -- target health state or error>
  - <failing probe -- command and its output that confirms the cause>
  - <passing probes -- layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <resource> in <region>.
  Proceed? (yes/no)"
```

### Worked example -- health check path misconfiguration

```text
TARGET: tg-prod-web-app (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-web-app/abc123)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: All 6 targets show unhealthy with Target.FailedHealthChecks.
  The HealthCheckPath is configured as /health but the application
  serves the health endpoint on /healthz. A direct curl to a target
  on /health returns 404; on /healthz returns 200.
LAYER: HEALTH_CHECK_PATH
EVIDENCE:
  - Symptom: describe-target-health shows all 6 targets in state
    "unhealthy" with Reason "Target.FailedHealthChecks".
  - Probe: curl -s -o /dev/null -w "%{http_code}"
    http://10.0.1.42:8080/health returns 404.
  - Probe: curl -s -o /dev/null -w "%{http_code}"
    http://10.0.1.42:8080/healthz returns 200.
  - Passing: security group sg-target allows inbound from sg-alb on
    port 8080 (SG is not the issue); HealthCheckPort is traffic-port
    (port is not the issue); HealthCheckProtocol is HTTP (protocol
    is not the issue).
REMEDIATION:
  1. Update the target group health check path:
     aws elbv2 modify-target-group \
       --target-group-arn arn:...:targetgroup/tg-prod-web-app/abc123 \
       --health-check-path /healthz
  2. Wait for HealthyThresholdCount consecutive successes (default 5
     checks at 30s interval = ~2.5 minutes).
  3. Verify with describe-target-health; all targets should show
    "healthy".
CONFIRM: Before updating the target group, emit and await:
  "CONFIRM: About to modify health-check-path on tg-prod-web-app.
   Proceed? (yes/no)"
```

### Worked example -- security group blocking health checks

Full worked example (all targets ConnectionFailed; target SG missing ALB SG on 443; LAYER: SG_BLOCKING_HEALTH_CHECK): [references/worked-examples.md](references/worked-examples.md).

### Worked example -- Lambda target group unhealthy

Full worked example (Lambda health-check invoke times out at 3s; LAYER: LAMBDA_TARGET_INTEGRATION): [references/worked-examples.md](references/worked-examples.md).

## Anti-Patterns -- NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER SSH into the target before verifying the ALB-side health check
  configuration. The majority of health check failures are
  configuration mismatches (path, port, protocol, SG), not target-
  side issues. Always run `describe-target-groups` and
  `describe-security-groups` first.

- NEVER confuse `draining` with `unhealthy`. A target in `draining`
  state is completing in-flight requests after deregistration. It is
  not failing health checks. The state is governed by
  `deregistration_delay.timeout_seconds`.

- NEVER set the health check path without verifying the application's
  actual endpoint. The path is case-sensitive (`/Health` != `/health`)
  and must return an HTTP status code matching the configured
  `Matcher.HttpCode` (default 200).

- NEVER assume the health check port equals the target port. The
  `HealthCheckPort` can be set to any port independently of the
  target registration port. A mismatch is a common root cause.

- NEVER allow the ALB health checker by IP range. ALB nodes use
  private IPs from the ALB subnet. Use the ALB security group ID as
  the source in the target SG ingress rule instead of CIDR blocks.

- NEVER treat `unused` targets as unhealthy. A target showing `unused`
  is registered and may be healthy, but is not receiving traffic due
  to weighted routing rules or cross-zone configuration. The fix is
  in the listener rules, not the health check.

- NEVER forget that Lambda target groups ignore health check path and
  port. The ALB invokes the Lambda function directly. Health check
  failures for Lambda targets are always function-side (timeout,
  exception, non-200 response), not path/port misconfiguration.

- NEVER ignore the `Matcher.HttpCode` default of 200. Applications
  that return 204 (No Content), 301 (redirect), or other codes on the
  health endpoint fail health checks against the default matcher.
  Update the matcher to include the expected codes.

- NEVER assume cross-zone is always enabled. While ALB enables
  cross-zone by default, it can be disabled. With cross-zone off, ALB
  nodes only route to targets in their own AZ. Targets in an AZ
  without an ALB node show `unused`.

- NEVER conflate deregistration delay with connection draining. They
  are the same concept under different attribute names for different
  load balancer types. For ALB, the attribute is
  `deregistration_delay.timeout_seconds`.

- NEVER enable `proxy_protocol_v2` without configuring the target to
  parse PROXY protocol headers. The ALB prepends a binary header that
  the application must consume; otherwise the application receives
  garbled data and fails health checks.

- NEVER set `preserve_client_ip.enabled` without updating the target
  security group. With this attribute, the target sees the client's
  real IP, not the ALB's. The target SG must allow the client CIDR
  range, not just the ALB SG.

## Pre-flight safety checks (run before any state-changing CLI)

Safety gate rules (confirmation gate, read-only probes, blast radius of each modify command, bulk batch limit): [references/advanced-patterns.md](references/advanced-patterns.md).

## Remediation guidance

Per-LAYER fix commands (HEALTH_CHECK_PATH, PORT_MISMATCH, PROTOCOL_MISMATCH, SG_BLOCKING_HEALTH_CHECK, DEREGISTRATION_DELAY, HEALTH_CHECK_THRESHOLD, LAMBDA_TARGET_INTEGRATION, WEIGHTED_ROUTING, SLOW_START, CROSS_ZONE): [references/error-handling.md](references/error-handling.md).

## Deep reference: ALB target health layer model

Layer model deep reference (symptom->layer matrix, parameter defaults/ranges, target group attributes, TargetType differences, ECS grace period, listener protocol compatibility): [references/target-group-attribute-reference.md](references/target-group-attribute-reference.md).

## Recent AWS features (2024-2026)

Full feature list with dates: [references/advanced-patterns.md](references/advanced-patterns.md).

## Domain

AWS CloudOps / Application Load Balancer, Target Health Diagnostics,
Health Check Configuration, Security Group Network Access, and
Target Group Lifecycle.

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — pre-flight gather-info gate, state short-circuit, and every step's probe and fix commands (Steps 2-9)
- [Worked examples](references/worked-examples.md) — SG blocking health checks, Lambda target group unhealthy, both INSUFFICIENT_DATA templates
- [Error handling](references/error-handling.md) — per-LAYER remediation commands
- [Advanced patterns](references/advanced-patterns.md) — quick-start heuristics, mindset, philosophy, Step 0 non-obvious behaviours, pre-flight safety checks, recent AWS features
- [Target group attribute reference](references/target-group-attribute-reference.md) — attribute/parameter tables, TargetType differences, protocol compatibility, layer model

## AWS documentation

- **Application Load Balancer User Guide -- Target groups** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- **ALB health checks** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- **Target group attributes** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-attributes
- **ALB listener rules** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-update-rules.html
- **Lambda functions as targets** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html
- **Security groups for ALB** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-security-groups.html
- **Cross-zone load balancing** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-settings.html#cross-zone-load-balancing
- **Deregistration delay** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#deregistration-delay
- **Slow start mode** -- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#slow-start-mode
- **ECS health check grace period** -- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html#service_scheduler_ets
