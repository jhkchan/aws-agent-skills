# Advanced Patterns — ALB 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

A "5xx from the ALB" page is almost always a target or configuration
incident wearing a load balancer costume. The ALB itself is rarely the
cause — it is the messenger reporting that the targets are unhealthy,
unreachable, slow, or returning invalid responses. The broken thing is
the target application, the target security group, the health check
configuration, or the listener rule. Treat the ALB as a relay until the
target health, security group, and listener layers are proven clean.

## Philosophy

Four behaviours separate a senior ELBv2 engineer from a generalist:

- **The 5xx code tells you WHERE the failure happened.** A 502 means the
  target returned an invalid response (connection reset, malformed HTTP,
  non-HTTP bytes) or the connection failed (target port closed, SSL
  error). A 503 means no healthy target is available to receive traffic
  (all targets unhealthy, draining, or unregistered). A 504 means the
  target did not respond within the idle timeout (default 60s). A 561
  means WAF blocked the request. A 500 means the ALB itself failed (rare).
  Routing the code to the wrong layer is the #1 source of wasted cycles.

- **Target health check configuration is the most common 5xx root cause.**
  A health check on `/health` that returns 200 does NOT mean the
  application is healthy on its actual endpoints. The target passes the
  health check but returns 500 on real requests. Conversely, a health
  check path that 404s marks the target unhealthy even when the
  application is fine — the ALB returns 503 because it has no healthy
  targets. Always compare the health check path against the actual
  application routes.

- **Security group rules are bidirectional and frequently misconfigured.**
  The ALB security group controls client-to-ALB traffic. The target
  security group controls ALB-to-target traffic. A common
  misconfiguration: the target SG allows 0.0.0.0/0 "because the ALB
  handles security" — this exposes the target directly, bypassing the
  ALB. Conversely, the target SG allowing only the ALB's public IP (not
  the ALB SG) breaks when the ALB scales and its IP changes. The
  correct pattern: target SG inbound allows the ALB SG on the target
  port.

- **Access logs are the forensic trail.** Without ALB access logs in S3,
  you have only aggregate CloudWatch metrics — no per-request
  `target_processing_time`, `target_status_code`, or `error_reason`.
  The `error_reason` field in ALB access logs pinpoints the exact 5xx
  cause (`Target.InvalidResponse`, `Target.ConnectionFailed`,
  `Target.Timeout`). Operators who "see 5xx in CloudWatch but no detail"
  almost always have access logs disabled. Enable them as the first
  remediation step.

## Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior ELBv2 engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **A health check on `/health` passing does NOT mean the application is
  healthy.** The health check probes one path; the application serves
  many. A common pattern: `/health` returns 200 (static page), but the
  actual endpoints return 500 (database connection failed). The target
  is marked `healthy`, traffic flows, and clients see 500/502 from the
  target — not from the ALB. The fix is a deep health check (e.g.,
  `/health/deep` that checks the database), not a target restart.

- **NLB TCP health checks succeed even when the application is broken.**
  The default NLB health check is TCP — a successful three-way handshake
  marks the target `healthy`. An application returning 500s, serving the
  wrong content, or hung after the handshake all pass a TCP check. For
  HTTP/HTTPS applications behind an NLB, ALWAYS verify
  `health_check.type` is HTTP/HTTPS with a real `path`. A TCP check on
  an HTTP target produces false-healthy status — the ALB routes traffic
  to a broken target, and users see 502/504.

- **Target security group rules must reference the ALB SG, not the ALB's
  IPs.** ALB IPs change when the ALB scales. A target SG rule allowing a
  specific ALB IP breaks when the ALB adds a node. The correct pattern:
  target SG inbound allows the ALB SG ID (`Source: sg-alb-xxx`) on the
  target port. Operators who "see the SG allows the ALB" but still get
  502 often have a stale IP-based rule from before the ALB scaled.

- **The deregistration delay (default 300s) keeps targets in `draining`
  state.** During deregistration, targets receive in-flight requests but
  no new ones. An ALB with all targets `draining` has no healthy targets
  for new requests — it returns 503. The signature is
  `describe-target-health` showing `State: draining` for all targets.
  This happens during deployments if the new targets are not registered
  before the old ones are deregistered.

- **ALB access logs are in S3, not CloudWatch Logs.** Unlike API Gateway
  (which logs to CloudWatch Logs), ALB access logs are delivered to an
  S3 bucket. The bucket must have the correct policy granting
  `elasticloadbalancing.amazonaws.com` write access with
  `aws:SourceAccount` condition. Operators who "can't find the logs"
  often have the S3 bucket policy misconfigured — logs are enabled but
  never delivered.

- **The `error_reason` field in ALB access logs pinpoints the 5xx cause.**
  For 502 and 503, the access log includes an `error_reason` field:
  - `Target.InvalidResponse` — target returned malformed HTTP.
  - `Target.ConnectionFailed` — connection to target refused/failed.
  - `Target.Timeout` — target did not respond within the idle timeout.
  - `Target.HealthCheckFailed` — target failed health checks.
  This field is the single highest-signal diagnostic for ALB 5xx.

- **ALB idle timeout (60s default) applies to BOTH frontend and backend.**
  The timeout applies to the client-to-ALB connection AND the
  ALB-to-target connection. If the target takes > 60s to respond, the
  ALB closes the connection with a 504. Long-polling, WebSocket, or
  slow-upload workloads need the timeout raised (up to 4000s).

- **NLB cross-zone load balancing is OFF by default.** Without cross-zone,
  traffic is distributed per-AZ. If one AZ has more targets or more
  capacity, the distribution is uneven. With cross-zone ON (always ON
  for ALB, toggleable for NLB), traffic distributes across all targets
  in all AZs. A 503 in one AZ while another AZ has healthy targets is
  the signature of cross-zone OFF on an NLB.

- **Listener rules are evaluated in priority order.** The lowest numeric
  priority rule that matches the request is applied. A misconfigured
  high-priority rule can shadow the intended target group — requests
  that should go to target group A go to target group B (which may be
  unhealthy or wrong). Always check `describe-rules` priority ordering
  when the "wrong" targets are receiving traffic.

- **A target registered by instance ID uses the instance's primary
  private IP.** If the application runs on a secondary IP or a container
  port, the instance-type registration sends traffic to the wrong place.
  Use IP-type registration for containers, secondary IPs, or non-VPC
  targets.

- **WAF 561 errors are not always obvious.** WAF blocks produce a 561
  (custom error) from the ALB, not a 403. Operators debug this as a
  backend failure because 561 is uncommon. Check the WAF Web ACL
  associated with the ALB — a rule blocking legitimate traffic (false
  positive) produces 561.

- **ALB HTTP 502 from a Lambda target means the function failed.** When
  an ALB invokes a Lambda function and the function crashes, returns an
  invalid response, or times out, the ALB returns 502. The Lambda
  Multi-Value Headers setting and the response format (similar to but
  different from API Gateway Lambda proxy) must match. Check Lambda
  logs, not ALB logs, for the function error.

- **Health check grace period matters for new deployments.** When a new
  target is registered, it starts in `initial` state. The health check
  must pass `healthy_threshold_count` consecutive times before the target
  becomes `healthy`. During this window, the ALB does not route traffic
  to the new target. If all old targets were deregistered, the ALB has
  no healthy targets and returns 503 until the new targets pass health
  checks.

- **A target in a different AZ than the ALB subnets cannot receive
  traffic without cross-zone.** ALB subnets are configured at creation.
  If the ALB has subnets in us-east-1a and us-east-1b, but the target is
  in us-east-1c, the ALB cannot route to it (for ALB, cross-zone handles
  this; for NLB without cross-zone, the target is unreachable from the
  ALB's AZs).

## Recent AWS features (2024-2026)

- **ALB target group health check enhancements (2024-2025):** Improved
  health check granularity including configurable success codes per
  target group. Operators should verify the matcher includes all success
  codes the application returns (200, 204, 301).
- **NLB TCP health check improvements (2024):** Optional HTTP/HTTPS
  health checks for NLB target groups. Operators migrating from ALB to
  NLB for static IPs should switch health check type from TCP to HTTP
  to avoid false-healthy status.
- **ALB access log field additions (2024):** New fields including
  `chosen_cert_arn` and enhanced `error_reason` values. Enable access
  logs with the latest format for the richest 5xx diagnosis surface.
- **WAF integration enhancements (2024-2025):** Custom response codes
  and headers for WAF blocks. The 561 error code is now customizable —
  operators may see 403 or other codes depending on WAF configuration.
- **Cross-zone load balancing for NLB (2024):** Continued support for
  toggling cross-zone on NLB. New NLBs default to OFF; operators should
  evaluate whether ON is needed for even distribution.
- **ALB Lambda target improvements (2024-2025):** Enhanced Lambda
  multi-value header support and response format validation. Lambda
  targets behind ALB now have clearer error messages for malformed
  responses.
