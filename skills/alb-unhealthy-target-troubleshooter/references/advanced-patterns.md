# Advanced Patterns — ALB Unhealthy Target Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Quick start (full heuristics)

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

## Step 0: Non-obvious behaviours that change diagnosis

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
