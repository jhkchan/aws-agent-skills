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

- **Symptom -> layer map (first plausible match drives the first probe):**
  All targets unhealthy with `Target.FailedHealthChecks` ->
  HEALTH_CHECK_PATH / PORT_MISMATCH / PROTOCOL_MISMATCH / SG_BLOCKING_HEALTH_CHECK;
  targets healthy but ALB returns 502 -> LAMBDA_TARGET_INTEGRATION /
  PROTOCOL_MISMATCH; targets stuck in `Draining` too long ->
  DEREGISTRATION_DELAY; targets flap healthy/unhealthy ->
  HEALTH_CHECK_THRESHOLD; new targets unhealthy then turn healthy after
  a delay -> SLOW_START; targets `Unused` -> WEIGHTED_ROUTING /
  CROSS_ZONE; Lambda target group shows unhealthy ->
  LAMBDA_TARGET_INTEGRATION.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence -- a failing probe that matches the
  symptom -- not a process of elimination.
- **The ALB health checker IP ranges must be allowed in the target
  security group.** ALB health checks originate from the ALB nodes
  themselves, using their private IPs. If the target security group
  does not allow inbound from the ALB SG (or the ALB subnet CIDR),
  every health check is connection-refused and all targets appear
  unhealthy. This is the #1 cause of all-targets-unhealthy incidents.
- **Health check port and target port are independent.** A common
  misconfiguration sets the health check port to the listener port
  (e.g., 443) while the application serves health on a separate port
  (e.g., 8080). The health check succeeds only when both port and path
  are correct for the application's actual health endpoint.
- **Deregistration delay is not a bug -- it is a feature.** When a
  target is deregistered, the ALB waits `deregistration_delay.timeout_seconds`
  (default 300) before removing it. During this window the target shows
  state `Draining`. Existing in-flight requests complete; new requests
  are not sent. Operators who see targets stuck in `Draining` are
  seeing normal behaviour, not a failure.

## Mindset

A target showing unhealthy in an ALB target group is usually a
configuration mismatch between what the health checker probes and what
the target serves. The application is fine in the majority of cases;
the broken thing is the health check path, port, protocol, security
group rule, or target group attribute. Treat the target as innocent
until the health check configuration, port mapping, protocol, and
security group ingress are proven correct. Senior network engineers do
not start by SSH-ing into the target; they start with
`describe-target-health` and `describe-security-groups`, and only
connect to the target once the ALB-side configuration is confirmed
correct.

## Philosophy

Four behaviours separate a senior ALB engineer from a generalist:

- **The target health reason code drives the diagnostic order.** A
  `Target.FailedHealthChecks` reason tells you the health checker
  reached the target but the response did not match the expected
  status code. An `Elb.InternalError` reason tells you the ALB itself
  has a problem. A `Target.InvalidState` reason tells you the target
  is in a state (stopped, terminated) that prevents health checking.
  Routing the symptom to the wrong layer is the #1 source of wasted
  cycles in ALB health incidents.

- **Security group rules for health checks are bi-directional.** The
  ALB's managed SG allows all egress by default. The target's SG must
  allow inbound from the ALB's SG on the health check port. Operators
  who "opened port 8080 to 0.0.0.0/0" but forgot to open it to the ALB
  SG specifically, or who opened the application port but not the
  health check port, see all targets fail health checks even though
  the application is running fine.

- **Deregistration delay and connection draining are two names for
  the same concept.** The attribute was renamed from
  `connection_draining.enabled` (Classic ELB) to
  `deregistration_delay.timeout_seconds` (ALB/NLB). Both control how
  long the load balancer waits for in-flight requests to complete
  after a target is deregistered. A long deregistration delay is not
  a health check failure; it is the load balancer giving the target
  time to drain.

- **Lambda target groups do not use TCP health checks.** A Lambda
  target is health-checked by the ALB invoking the function with a
  health check event. If the function fails, throws, or times out on
  the health check invocation, the target shows unhealthy. The health
  check path and port attributes are ignored for Lambda targets; the
  protocol must be HTTP or HTTPS, and the function must return a 200.

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

```bash
# 1. Target group configuration (TargetType, HealthCheckPath,
#    HealthCheckPort, HealthCheckProtocol, HealthCheckTimeoutSeconds,
#    HealthCheckIntervalSeconds, HealthyThresholdCount,
#    UnhealthyThresholdCount, Matcher, Protocol, Port, VpcId)
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json

# 2. Target health for all registered targets
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> --output json

# 3. Target group attributes (deregistration delay, stickiness,
#    proxy protocol, preserve client IP, slow start)
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json

# 4. Security groups for the targets (ingress rules)
aws ec2 describe-security-groups \
  --group-ids <target-sg-id> --output json

# 5. ALB configuration (subnets, security groups, AZs)
aws elbv2 describe-load-balancers \
  --load-balancer-arns <alb-arn> --output json

# 6. Listener rules (weighted routing, host-header, path-pattern)
aws elbv2 describe-rules \
  --listener-arn <listener-arn> --output json

# 7. CloudWatch target health metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name UnHealthyHostCount \
  --dimensions Name=TargetGroup,Value=<tg-id> Name=LoadBalancer,Value=<alb-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum,Maximum --output json
```

### Target-health-state short-circuit

| TargetHealth `State` / `Reason` | Effect on diagnosis |
|---|---|
| `healthy` | Target passed health checks. If app still fails, the issue is routing (listener rules), not health. |
| `unhealthy` + `Target.FailedHealthChecks` | Health checker reached the target but the response did not match the expected status code (Matcher). Check path, port, protocol, and the application's actual response. |
| `unhealthy` + `Target.ConnectionFailed` | Health checker could not establish a TCP connection. Check security group, health check port, and target instance state. |
| `unhealthy` + `Target.InvalidState` | The target EC2 instance is stopped or terminated. Check EC2 instance state; not a health check config issue. |
| `unused` | The target is registered but not receiving traffic. Check listener rules (weighted routing), target group attachment to a listener, and cross-zone settings. |
| `draining` | The target was deregistered and is completing in-flight requests. Check `deregistration_delay.timeout_seconds`; not a health check failure. |
| `initial.health_check` (ALB) / `healthy.initial` (NLB) | The target is in the initial health check grace period. Wait for `HealthyThresholdCount` consecutive successes before declaring an issue. |

If the input is malformed (missing TargetGroupArn, absent symptom
description, no target health context), emit:

```text
TARGET: <target-group-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context -- at minimum a symptom
  description (the target health state or observed behaviour) and the
  TargetGroupArn.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact target health
  state (describe-target-health output), (2) the TargetGroupArn, and
  (3) the target group configuration (describe-target-groups output).
```

## Process -- Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation or a
pass that moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED
without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior ALB engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **The ALB health checker uses the ALB node's private IP, not a
  well-known CIDR.** Unlike NLB health checks (which use the NLB
  private IPs), ALB health checks originate from the ALB nodes in the
  ALB's subnets. The target SG must allow inbound from the ALB SG
  (recommended) or the ALB subnet CIDRs. Operators who look for a
  published "health checker IP range" and try to allow specific IPs
  are on the wrong track -- reference the ALB SG instead.

- **The health check path is case-sensitive.** `/Health` and `/health`
  are different paths. An application that serves a health endpoint on
  `/health` fails health checks configured with `/Health` (404 response,
  which does not match the default Matcher of 200). Operators who
  "copy-pasted from the docs" with a capitalised path see all targets
  fail.

- **The health check port overrides the target port.** If
  `HealthCheckPort` is set to `traffic-port` (the default), health
  checks go to the target's registered port. If set to a specific port
  (e.g., `80`), health checks always go to port 80 regardless of the
  target port. A target registered on port 8080 with `HealthCheckPort:
  80` fails health checks unless the application also listens on 80.

- **The Matcher defaults to HTTP 200 only.** The `Matcher.HttpCode`
  defaults to `200`. If the application returns `204 No Content` on
  the health endpoint (common for some frameworks), the health check
  fails. Set `Matcher.HttpCode` to `200,204` to accept both.

- **HTTPS health checks do not validate certificates by default.** If
  `HealthCheckProtocol` is HTTPS, the ALB does not validate the target's
  TLS certificate. A self-signed cert is fine. But the target must
  still respond on the HTTPS port -- a target serving HTTP on port 443
  causes the health check to fail with a protocol error.

- **Deregistration delay applies per target, not per target group.**
  When a single target deregisters, it enters `Draining` for
  `deregistration_delay.timeout_seconds`. Other targets in the group
  are unaffected. A deployment that replaces all targets (e.g.,
  ASG instance refresh) creates a wave of draining targets that all
  drain in parallel.

- **Slow start mode ramps traffic gradually to new healthy targets.**
  With `slow_start.duration_seconds` set (ALB only, instance/IP target
  type), newly-healthy targets receive a ramping fraction of traffic
  over the configured duration. During ramp-up the target appears
  healthy but underutilised. Operators who expect immediate full
  traffic after healthy status are confused by slow start.

- **Lambda target groups have no health check path or port.** The ALB
  invokes the Lambda function for every health check with a GET
  request. The function must return a 200 status code. A function that
  throws, times out, or returns a non-200 causes the target to show
  unhealthy. The `HealthCheckPath`, `HealthCheckPort`, and `Matcher`
  attributes are ignored for Lambda targets.

- **Weighted target groups route a percentage of traffic, not a
  count.** A listener rule with two weighted forward actions (80/20)
  sends approximately 80% of requests to one TG and 20% to another.
  Targets in the 20% TG show as `Unused` if the total request volume
  is low enough that the 20% share is less than one request per
  health-check interval.

- **Cross-zone load balancing distributes traffic across all AZs by
  default (ALB).** If cross-zone is disabled (`load_balancing.cross_zone.enabled`
  = false), each ALB node only sends traffic to targets in its own AZ.
  Targets in an AZ with no ALB node show as `Unused`. This is a rare
  misconfiguration but produces confusing symptoms.

- **Stickiness can mask health check failures.** With stickiness
  enabled (`stickiness.enabled` = true), a client pinned to a target
  continues sending requests to that target even after it becomes
  unhealthy, until the stickiness cookie expires. This delays the
  client-visible impact of a health check failure.

- **Proxy protocol v2 and preserve client IP affect the connection.**
  With `proxy_protocol_v2.enabled` = true, the ALB prepends a PROXY
  protocol header. The target must be configured to parse it.
  With `preserve_client_ip.enabled` = true, the target sees the
  client's real IP instead of the ALB's IP. Both affect security
  group rules: with preserve client IP, the target SG must allow the
  client CIDR (not the ALB SG).

- **Target health check grace period for ECS tasks.** ECS allows a
  `healthCheckGracePeriodSeconds` on a service using an ALB. During
  this period, ECS ignores ALB health check failures for newly started
  tasks. If the grace period is too short, tasks are killed before
  the application finishes starting. If too long, a genuinely broken
  task is not detected.

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

```bash
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[] | {
    HealthCheckPath, HealthCheckPort, HealthCheckProtocol,
    HealthCheckTimeoutSeconds, HealthCheckIntervalSeconds,
    HealthyThresholdCount, UnhealthyThresholdCount,
    Matcher, Protocol, Port, TargetType, VpcId
  }'
```

Cross-reference each field against the application's actual
configuration:

| Config field | Common mismatch |
|---|---|
| `HealthCheckPath` | Application serves `/healthz` but TG configured with `/health` (or vice versa). Case-sensitive. |
| `HealthCheckPort` | Set to `traffic-port` (default) but the app serves health on a different port than the data port. |
| `HealthCheckProtocol` | Set to HTTP but the app only serves HTTPS (or vice versa). |
| `Matcher.HttpCode` | Defaults to `200`; app returns `204`, `301`, or another code. |
| `HealthCheckTimeoutSeconds` | Too short for the app's health endpoint response time (default 5s for HTTP, 2s for HTTPS but must be < interval). |
| `Protocol` (target protocol) | TG protocol HTTP but app expects HTTPS, or TG protocol HTTPS but app serves HTTP. |

#### 2b: Verify the health check path and response

```bash
# From a host in the same VPC, curl the target's health endpoint directly
curl -v http://<target-private-ip>:<target-port><health-check-path>
curl -v http://<target-private-ip>:<health-check-port><health-check-path>

# Check the HTTP response code
curl -s -o /dev/null -w "%{http_code}" \
  http://<target-private-ip>:<target-port><health-check-path>
```

If the direct curl returns a non-200 code, the application is not
serving the expected response. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: HEALTH_CHECK_PATH`. Fix: update the application to return 200
on the health endpoint, or update the TG `Matcher.HttpCode` to accept
the actual response code.

#### 2c: Verify the health check port

If `HealthCheckPort` is `traffic-port`, the health check uses the
target's registered port. If it is a specific number, health checks
go to that port.

```bash
# Verify the application listens on the health check port
# (from the target instance itself)
ss -tlnp | grep <health-check-port>
# or
netstat -tlnp | grep <health-check-port>
```

If the application is not listening on the health check port,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: PORT_MISMATCH`. Fix: either
change `HealthCheckPort` to `traffic-port` (or the correct port), or
start the application listener on the health check port.

#### 2d: Verify the protocol

If `HealthCheckProtocol` is `HTTP` but the application only serves
`HTTPS` (redirects all HTTP to HTTPS), the health check gets a 301
redirect which does not match `Matcher.HttpCode: 200`.

If `HealthCheckProtocol` is `HTTPS` but the application serves
`HTTP`, the TLS handshake fails.

**ROOT_CAUSE_IDENTIFIED** with `LAYER: PROTOCOL_MISMATCH`. Fix: align
`HealthCheckProtocol` with the application's actual protocol.

### Step 3: Security group blocking health checker IPs

Symptom: all targets show `unhealthy` with reason
`Target.ConnectionFailed` or `Target.FailedHealthChecks` where the
failure is a TCP connection refused/timeout.

#### 3a: Identify the ALB security group and subnets

```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns <alb-arn> --output json | \
  jq '.LoadBalancers[] | {
    SecurityGroups, AvailabilityZones, VpcId,
    State: .State.Code
  }'
```

#### 3b: Check the target security group ingress rules

```bash
aws ec2 describe-security-groups \
  --group-ids <target-sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

The target SG must allow inbound on the health check port from either:
- The ALB's security group ID (recommended -- use a SG reference)
- The ALB's subnet CIDRs (acceptable)
- 0.0.0.0/0 (works but overly permissive)

If the target SG does not allow inbound from the ALB SG on the health
check port, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: SG_BLOCKING_HEALTH_CHECK`.

Fix: add an ingress rule:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <target-sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<health-check-port>,ToPort=<health-check-port>,UserIdGroupPairs=[{GroupId=<alb-sg-id>}]
```

#### 3c: Verify with ALB ENI IPs

```bash
# Get the ALB's ENI private IPs
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="ELB app/<alb-name>/*" \
  --output json | \
  jq '.NetworkInterfaces[].PrivateIpAddress'
```

From the target instance, attempt a connection:

```bash
# From the target instance
curl -v http://<alb-eni-ip>:<health-check-port><health-check-path>
```

If this fails, the SG or network ACL is blocking the health check.

#### 3d: Network ACL check

If the SG is correct but health checks still fail, check the NACL on
both the ALB subnet and the target subnet. NACLs are stateless; both
inbound and outbound rules must allow ephemeral ports (1024-65535) for
return traffic.

### Step 4: Per-target and per-AZ issues

Symptom: some targets are `healthy` and others are `unhealthy` in the
same target group.

#### 4a: Identify the failing targets' AZs

```bash
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn> --output json | \
  jq '.TargetHealthDescriptions[] | {
    Target: .Target.Id, Port: .Target.Port,
    AZ: .Target.AvailabilityZone,
    Health: .TargetHealth.State,
    Reason: .TargetHealth.Reason
  }'
```

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

```bash
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("deregistration"))'
```

The `deregistration_delay.timeout_seconds` attribute controls how long
the ALB waits (default 300 seconds = 5 minutes). During this window:
- In-flight requests are allowed to complete.
- New requests are not sent to the draining target.
- The target shows state `draining`.

If the delay is set very high (e.g., 3600 seconds), targets appear
stuck. This is not a failure -- it is configured behaviour. If the
operator needs faster removal, lower the delay:

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=60
```

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DEREGISTRATION_DELAY`.
The targets are draining normally per the configured timeout. No fix
needed unless the operator wants faster deregistration.

### Step 6: Health check threshold and interval tuning

Symptom: targets flap between `healthy` and `unhealthy` intermittently.
The health check is borderline -- occasionally failing enough
consecutive checks to mark unhealthy, then recovering.

#### 6a: Read the threshold and interval config

```bash
aws elbv2 describe-target-groups \
  --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[] | {
    HealthCheckIntervalSeconds,
    HealthCheckTimeoutSeconds,
    HealthyThresholdCount,
    UnhealthyThresholdCount
  }'
```

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

```bash
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("slow_start"))'
```

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

```bash
aws elbv2 describe-rules \
  --listener-arn <listener-arn> --output json | \
  jq '.Rules[].Actions[] | select(.Type == "forward") | .ForwardConfig'
```

If `ForwardConfig.TargetGroups` has multiple entries with different
weights, traffic is split proportionally. A target group with weight
0 receives no traffic and its targets show `unused`.

#### 8b: Check cross-zone load balancing

```bash
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn <alb-arn> --output json | \
  jq '.Attributes[] | select(.Key | startswith("load_balancing"))'
```

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

```bash
aws lambda get-function-configuration \
  --function-name <function-arn> --output json | \
  jq '{State, LastUpdateStatus, Timeout, Runtime}'

aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Task timed out" OR "Runtime.ExitError" OR "Error"' \
  --output json
```

Common Lambda target group failure patterns:

| Pattern | Cause |
|---|---|
| Function times out on health check invocation | Lambda Timeout too low. The ALB health check is a synchronous invoke; if it times out, the target is unhealthy. |
| Function returns non-200 status code | The function handler returns a response with `statusCode` != 200. The ALB expects 200 for health. |
| Function throws an exception | Unhandled exception in the handler. The ALB receives a 502 from Lambda and marks the target unhealthy. |
| Multi-value headers misconfigured | The function response must properly format headers for the ALB integration. |
| Function does not handle the ALB health check event | The ALB sends a GET request event; the function must be able to handle it and return 200. |

**Verdict:** ROOT_CAUSE_IDENTIFIED,
`LAYER: LAMBDA_TARGET_INTEGRATION`. Fix: ensure the function returns
200 on the health check invocation, does not time out, and properly
handles the ALB event format.

### Step 10: Protocol mismatch causing 502s

Symptom: the ALB returns 502 Bad Gateway even though targets show
`healthy`.

The listener protocol and target group protocol must be compatible:

| Listener protocol | TG protocol | Works? |
|---|---|---|
| HTTPS | HTTP | Yes (TLS termination at ALB) |
| HTTPS | HTTPS | Yes (end-to-end TLS) |
| HTTP | HTTP | Yes |
| HTTP | HTTPS | Yes (but requires HTTPS TG) |
| HTTPS | HTTPS with self-signed cert | Yes (ALB does not verify cert) |

A 502 from the ALB when targets are healthy usually means the target
closed the connection unexpectedly. Common causes:
- The application has a keep-alive timeout shorter than the ALB's.
- The application does not support HTTP/1.1 (ALB uses HTTP/1.1 to
  targets).
- The target is an HTTPS endpoint but the TG protocol is HTTP,
  causing a protocol mismatch.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PROTOCOL_MISMATCH`. Fix:
align the target group protocol with the application's actual protocol.

### Step 11: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

```text
TARGET: <target-group-arn>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a
  single root cause from the diagnostic tree. List the probes already
  executed and their results, and request additional context.
LAYER: UNKNOWN
EVIDENCE:
  - <probes executed and results>
  - <missing information needed>
REMEDIATION: Provide (1) the full describe-target-health output,
  (2) the full describe-target-groups output, (3) the target security
  group rules, (4) the ALB security group and subnets, and (5) the
  application's health endpoint response (curl from within the VPC).
```

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

```text
TARGET: tg-prod-api (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-api/def456)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: All 4 targets show unhealthy with Target.ConnectionFailed.
  The target security group sg-app-443 allows inbound on port 443
  from 10.0.0.0/8 but NOT from the ALB security group sg-alb (which
  is in a different VPC CIDR). Health check port is 443; the ALB
  health checker IP is in 172.16.x.x, which is not allowed by the
  target SG ingress rule.
LAYER: SG_BLOCKING_HEALTH_CHECK
EVIDENCE:
  - Symptom: describe-target-health shows all 4 targets in state
    "unhealthy" with Reason "Target.ConnectionFailed".
  - Probe: describe-security-groups on sg-app-443 shows inbound rule
    allowing 10.0.0.0/8 on port 443, but ALB ENI IPs are in
    172.16.1.x (confirmed via describe-network-interfaces).
  - Probe: curl from an EC2 instance in the ALB subnet to a target
    on port 443 times out (connection refused).
  - Passing: HealthCheckPath /api/health returns 200 when curled
    directly from a host in the target subnet (path is correct);
    application process is running on all targets.
REMEDIATION:
  1. Add an ingress rule to the target SG allowing the ALB SG:
     aws ec2 authorize-security-group-ingress \
       --group-id sg-app-443 \
       --ip-permissions \
       IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=sg-alb}]
  2. Wait 10-30 seconds for propagation, then verify with
    describe-target-health; targets should transition to healthy.
CONFIRM: Before modifying the security group, emit and await:
  "CONFIRM: About to add ingress rule to sg-app-443 allowing sg-alb
   on port 443. Proceed? (yes/no)"
```

### Worked example -- Lambda target group unhealthy

```text
TARGET: tg-lambda-processor (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-lambda-processor/ghi789)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Lambda target function fn-alb-processor times out on
  health check invocations. The function Timeout is 3 seconds; the
  ALB health check is a synchronous invoke that triggers the full
  handler, which takes 5-8 seconds due to a database query.
LAYER: LAMBDA_TARGET_INTEGRATION
EVIDENCE:
  - Symptom: describe-target-health shows the Lambda target in state
    "unhealthy" with Reason "Target.FailedHealthChecks".
  - Probe: aws logs filter-log-events on /aws/lambda/fn-alb-processor
    shows "Task timed out after 3.00 seconds" on health check
    invocations.
  - Probe: get-function-configuration shows Timeout: 3, Runtime:
    nodejs20.x.
  - Passing: function succeeds on non-health invocations that take
    < 3s; no errors in the function code.
REMEDIATION:
  1. Raise the Lambda function Timeout to 10 seconds:
     aws lambda update-function-configuration \
       --function-name fn-alb-processor --timeout 10
  2. Alternatively, add a fast-path in the handler that returns 200
    immediately for health check requests (detect via event path or
    HTTP method), avoiding the database query.
  3. Verify with describe-target-health after the next health check
    cycle; target should show "healthy".
CONFIRM: Before updating the function configuration, emit and await:
  "CONFIRM: About to raise fn-alb-processor timeout to 10s. Proceed?
   (yes/no)"
```

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-target-group`, `modify-target-group-attributes`,
  `authorize-security-group-ingress`, `modify-listener`,
  `create-rule`, `modify-rule`), emit and await operator approval.
  Do NOT execute the CLI until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-target-health`, `describe-target-groups`,
  `describe-security-groups`, `describe-network-interfaces`,
  `get-metric-statistics`). Do not perform state-changing operations
  as diagnostic probes.

- **`modify-target-group --health-check-path`** is safe and takes
  effect immediately. Existing targets are re-checked with the new
  path on the next health check interval.

- **`modify-target-group --health-check-port`** is safe but may cause
  a brief period of health check failures if the new port is
  incorrect. Verify the application listens on the new port first.

- **`authorize-security-group-ingress`** affects the security posture
  of the target. Always scope to the ALB SG (preferred) or the
  minimum necessary CIDR. Never add 0.0.0.0/0 for health checks.

- **`modify-target-group-attributes` for deregistration delay**
  affects how long deregistering targets take to drain. Lowering the
  value speeds up removal but may drop in-flight requests. Raising it
  extends the drain window.

- **`modify-target-group-attributes` for slow start** affects traffic
  ramp-up to new targets. Setting duration to 0 disables slow start;
  new targets immediately receive full traffic. This can overwhelm
  applications that need warm-up time.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple target groups (e.g., SG blocking
  after an ALB migration), batch remediation into groups of at most
  5 target groups, emit a single CONFIRM per batch, and verify
  between batches.

## Remediation guidance

### For HEALTH_CHECK_PATH

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-path <correct-path>
```

Verify the correct path first with a direct curl from within the VPC.

### For PORT_MISMATCH

```bash
# Option 1: Use traffic-port (the target's registered port)
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-port traffic-port

# Option 2: Use a specific port
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-port <port>
```

### For PROTOCOL_MISMATCH

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-protocol <HTTP|HTTPS>
```

Also update the Matcher if the application returns non-200 codes:

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --matcher HttpCode=200,204
```

### For SG_BLOCKING_HEALTH_CHECK

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <target-sg-id> \
  --ip-permissions \
    IpProtocol=tcp,FromPort=<port>,ToPort=<port>,UserIdGroupPairs=[{GroupId=<alb-sg-id>}]
```

### For DEREGISTRATION_DELAY

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=<seconds>
```

Range: 0-3600 seconds. Default: 300.

### For HEALTH_CHECK_THRESHOLD

```bash
aws elbv2 modify-target-group \
  --target-group-arn <tg-arn> \
  --health-check-interval-seconds <30-300> \
  --health-check-timeout-seconds <2-60> \
  --healthy-threshold-count <2-10> \
  --unhealthy-threshold-count <2-10>
```

Typical resilient configuration: interval 30s, timeout 5s, healthy
threshold 3, unhealthy threshold 3.

### For LAMBDA_TARGET_INTEGRATION

- Raise Lambda Timeout if the health check invoke times out.
- Add a fast-path in the handler for health check events.
- Ensure the function returns `statusCode: 200` on health checks.

### For WEIGHTED_ROUTING

```bash
aws elbv2 modify-rule \
  --rule-arn <rule-arn> \
  --actions Type=forward,TargetGroupArn=<tg-arn>,ForwardConfig={TargetGroups=[{TargetGroupArn=<tg-arn-1>,Weight=80},{TargetGroupArn=<tg-arn-2>,Weight=20}]}
```

### For SLOW_START

```bash
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=slow_start.duration_seconds,Value=<0|30-900>
```

Set to 0 to disable slow start. Range when enabled: 30-900 seconds.

### For CROSS_ZONE

```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true
```

## Deep reference: ALB target health layer model

### Symptom -> layer decision matrix (offline classification)

```
TargetHealthReason                        -> Layer
Target.FailedHealthChecks (all targets)   -> HEALTH_CHECK_PATH / PORT_MISMATCH / PROTOCOL_MISMATCH
Target.ConnectionFailed (all targets)     -> SG_BLOCKING_HEALTH_CHECK / PORT_MISMATCH
Target.FailedHealthChecks (some targets)  -> per-target app issue or AZ issue
Target.InvalidState                       -> target stopped/terminated (not a health check issue)
Unused                                    -> WEIGHTED_ROUTING / CROSS_ZONE
Draining                                  -> DEREGISTRATION_DELAY
healthy but flapping                      -> HEALTH_CHECK_THRESHOLD
healthy but low traffic                   -> SLOW_START
Lambda target unhealthy                   -> LAMBDA_TARGET_INTEGRATION
```

### Health check parameter defaults and ranges

| Parameter | Default | Range | Notes |
|---|---|---|---|
| `HealthCheckIntervalSeconds` | 30 | 5-300 | Lower = faster detection but more load |
| `HealthCheckTimeoutSeconds` | 5 | 2-60 | Must be < interval |
| `HealthyThresholdCount` | 5 | 2-10 | Consecutive successes to mark healthy |
| `UnhealthyThresholdCount` | 2 | 2-10 | Consecutive failures to mark unhealthy |
| `HealthCheckPath` | `/` | 1-1024 chars | Case-sensitive |
| `HealthCheckPort` | `traffic-port` | `traffic-port` or 1-65535 | Overrides target port |
| `Matcher.HttpCode` | `200` | `200`-`599`, comma-separated | Default does not match 204, 301 |

### Target group attributes reference

| Attribute | Default | Range | Effect |
|---|---|---|---|
| `deregistration_delay.timeout_seconds` | 300 | 0-3600 | Time to drain in-flight requests after deregistration |
| `stickiness.enabled` | false | true/false | Pin clients to targets via cookie |
| `stickiness.type` | lb_cookie | lb_cookie / app_cookie | Cookie mechanism |
| `stickiness.duration_seconds` | 86400 | 1-604800 | Cookie lifetime (lb_cookie) |
| `load_balancing.algorithm.type` | round_robin | round_robin / least_outstanding_requests | Load distribution algorithm |
| `slow_start.duration_seconds` | 0 | 0, 30-900 | Ramp-up time for new healthy targets |
| `proxy_protocol_v2.enabled` | false | true/false | PROXY protocol v2 header prepended |
| `preserve_client_ip.enabled` | false | true/false | Target sees client IP instead of ALB IP |
| `target.group_arn` | (read-only) | n/a | The TG ARN |

### TargetType differences

| TargetType | Health check mechanism | Notes |
|---|---|---|
| `instance` | TCP + HTTP/HTTPS probe to HealthCheckPort | EC2 instances; health check port configurable |
| `ip` | TCP + HTTP/HTTPS probe to HealthCheckPort | IP addresses; supports targets outside the VPC |
| `lambda` | Synchronous Lambda invoke with GET | No health check path/port; function must return 200 |
| `alb` | Cascaded health check via the nested TG | Target group as a target (weighted routing); health check delegates to the nested TG |

### ECS health check grace period

For ECS services with ALB targets, `healthCheckGracePeriodSeconds`
controls how long ECS ignores ALB health check failures for newly
started tasks:

```bash
aws ecs describe-services \
  --cluster <cluster> --services <service> --output json | \
  jq '.services[].healthCheckGracePeriodSeconds'
```

If the grace period is too short, tasks are killed before the
application finishes starting. Typical values: 30-300 seconds
depending on application startup time.

### ALB listener protocol compatibility

| Listener Protocol | TG Protocol | TLS Termination | Notes |
|---|---|---|---|
| HTTP | HTTP | None | Plain text end-to-end |
| HTTPS | HTTP | At ALB | ALB terminates TLS; target receives HTTP |
| HTTPS | HTTPS | End-to-end | ALB terminates and re-encrypts; ALB does not verify target cert |

## Recent AWS features (2024-2026)

- **Least-outstanding-requests load balancing algorithm (2024):**
  ALB now supports `least_outstanding_requests` as a target group
  attribute, distributing requests to the target with the fewest
  pending requests. Useful for heterogeneous target capacities.
- **Target group health check enhanced metrics (2024-2025):**
  CloudWatch now exposes `HealthyHostCount` and `UnHealthyHostCount`
  per-AZ metrics for target groups, improving multi-AZ diagnosis.
- **ALB slow start support for all target types (2024):**
  Previously instance-only; now also supports IP targets. Slow start
  gradually ramps traffic to new targets.
- **Lambda target group multi-value headers (2024-2025):**
  Enhanced header handling for Lambda target groups, reducing 502s
  from header format mismatches.
- **Zonal shift and zonal autoshift (2024-2025):**
  ARC Zonal Shift can evacuate traffic from a specific AZ. After a
  shift, targets in the evacuated AZ show `unused` until the shift
  is cancelled.

## Domain

AWS CloudOps / Application Load Balancer, Target Health Diagnostics,
Health Check Configuration, Security Group Network Access, and
Target Group Lifecycle.

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
