---
name: alb-5xx-troubleshooter
description: Diagnoses ALB and NLB 5xx errors (500 InternalServerError, 502 BadGateway, 503 ServiceUnavailable, 504 GatewayTimeout, 561 Unauthorized) through a systematic diagnostic tree covering target health check failures (wrong path, port, matcher, timeout), target security group misconfiguration (ALB SG cannot reach target SG on target port), idle timeout exceeded (60s default), deregistration draining stuck, listener rule misconfiguration (wrong target group, wrong priority), WAF blocks, and invalid backend responses. Walks symptoms to root cause with describe-target-health, ALB access logs in S3 (target_processing_time, target_status_code, error_reason), security group analysis, and listener rule inspection. Emits ROOT_CAUSE_FOUND with the specific failure layer or ESCALATE. Use when ALB returns 5xx errors, targets unhealthy, no healthy targets, or intermittent target failures.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error codes and target group metadata. Live-account diagnosis uses aws elbv2 describe-target-health, describe-target-groups, describe-listeners, describe-rules, describe-load-balancers, describe-load-balancer-attributes, aws ec2 describe-security-groups, aws s3 cp (for ALB access logs), and aws cloudwatch get-metric-statistics (AWS CLI v2, SSO or key-based...
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
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing an ALB or NLB 5xx error (500, 502, 503, 504, 561), walking a symptom to the failed target, security group, health check, or listener layer with verify and fix commands, validating target health failures, identifying unhealthy target groups, diagnosing idle timeout exceeded, or triaging a "the load balancer returns 5xx" page where the root cause may be target health, SG rules, health check configuration, deregistration, WAF, or listener rules — not necessarily the load balancer itself.
  when_not_to_use: Configuration posture audits (use elbv2-load-balancer-auditor for TLS policy, access-log enablement, deletion protection, SG exposure), TLS/cipher negotiation issues (use elbv2-load-balancer-auditor INSECURE_LISTENER), or capacity/throughput sizing (use the optimize task type). This skill diagnoses runtime 5xx failures and target health, not config posture.
  activation_triggers: ALB 5xx error, ALB 502 BadGateway, ALB 503 ServiceUnavailable, ALB 504 GatewayTimeout, ALB 561 Unauthorized, NLB 5xx, target unhealthy, no healthy targets, target group health check failed, ALB access logs 5xx, target security group blocked, deregistration draining stuck, WAF blocked request ALB, troubleshoot ALB, troubleshoot load balancer 5xx
  invocation_schema: 'Input: either (a) a symptom description (5xx error code, observed pattern, failing target group), optionally paired with the load balancer and target group metadata (describe-load-balancers, describe-target-groups, describe-target-health output), OR (b) a load balancer ARN or target group ARN for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/ REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈ {TARGET_HEALTH_CHECK, TARGET_SG_BLOCKED, TARGET_NONE_HEALTHY, TARGET_TIMEOUT, TARGET_INVALID_RESPONSE, LISTENER_MISCONFIGURED, WAF_BLOCKED, DEREGISTRATION_STUCK, ALB_INTERNAL, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ALB, NLB, ELBv2, load balancer, 5xx, 500, 502, 503, 504, 561, BadGateway, ServiceUnavailable, GatewayTimeout, target health, target group, health check, security group, idle timeout, deregistration, draining, WAF, listener rule, access logs, troubleshooting
  tags: elbv2, alb, nlb, load-balancer, networking, troubleshooting, 5xx, target-health
---

# ALB 5xx Troubleshooter

## Quick start

- **Error code → layer map (first plausible match drives the first probe):**
  502 → TARGET_INVALID_RESPONSE / TARGET_SG_BLOCKED; 503 →
  TARGET_NONE_HEALTHY / TARGET_HEALTH_CHECK / DEREGISTRATION_STUCK /
  TARGET_SG_BLOCKED; 504 → TARGET_TIMEOUT; 561 → WAF_BLOCKED;
  500 → ALB_INTERNAL (rare — check AWS Health Dashboard).
- **Always verify with a probe, never guess.** Each layer has a single
  command (or access-log field) that proves or disproves it. A
  ROOT_CAUSE_FOUND verdict requires positive evidence — a failing probe
  that matches the symptom — not "must be the targets."
- **Target health is the root of most 5xx.** A 503 with no healthy
  targets, a 502 from an unreachable target, and a 504 from a slow
  target all originate in the target group. Probe `describe-target-health`
  first — it is the single highest-signal command.
- **ESCALATE for AWS-side incidents.** A sustained 500 with healthy
  targets, no recent change, and clean configs is an AWS-side event —
  surface the Health Dashboard link and open a Support case.

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

## Quick navigation

| If the symptom is... | Go to | First probe |
|---|---|---|
| 502 with `Target.InvalidResponse` or `Target.ConnectionFailed` | Step 2a | `describe-target-health` + direct curl on target |
| 502 with target SG not allowing ALB SG | Step 2b | `describe-security-groups` on target SG |
| 503 with all targets `unhealthy` | Step 3a | `describe-target-health` + health check config |
| 503 with all targets `draining` | Step 3c | `deregistration_delay.timeout_seconds` |
| 503 with zero registered targets | Step 3b | `describe-target-groups` TargetType |
| 504 with `Target.Timeout` in access logs | Step 4 | ALB idle timeout + target response time |
| 561 from WAF | Step 5 | WAF Web ACL logs |
| 502/503 from wrong target group on listener | Step 6 | `describe-rules` for listener priorities |
| 500 sustained, healthy targets, no change | Step 7 | AWS Health Dashboard — ESCALATE |
| Need the access log format and fields | Reference | `references/target-health-reference.md` |

## Pre-flight: load balancer type and gather-info gate

Before running code-specific probes, gather the canonical load balancer,
listener, target group, and target health metadata. Misidentifying the
load balancer type (ALB vs NLB) or the target type (instance vs ip vs
lambda) produces false root causes.

### Account-wide pre-flight commands

```bash
# 1. Load balancer configuration (type, scheme, state, subnets, SGs)
aws elbv2 describe-load-balancers --load-balancer-arns <arn> --output json

# 2. Listeners (protocols, SSL policies, default actions, certificates)
aws elbv2 describe-listeners --load-balancer-arn <arn> --output json

# 3. Listener rules (priorities, conditions, actions — the routing logic)
aws elbv2 describe-rules --listener-arn <listener-arn> --output json

# 4. Target groups (health check config, target type, port, protocol)
aws elbv2 describe-target-groups --load-balancer-arn <arn> --output json

# 5. Target health (the single highest-signal command)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# 6. Load balancer attributes (idle timeout, deregistration delay, access logs)
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <arn> --output json

# 7. Security groups on the ALB
aws ec2 describe-security-groups \
  --group-ids $(aws elbv2 describe-load-balancers \
    --load-balancer-arns <arn> --output json | \
    jq -r '.LoadBalancers[0].SecurityGroups[]') --output json

# 8. CloudWatch metrics — HTTPCode_Target_5XX_Count, TargetResponseTime
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=<arn-suffix> Name=TargetGroup,Value=<tg-suffix> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 9. AWS Health (regional events for ELB)
aws health describe-events --filter services=ELASTICLOADBALANCING,\
  eventStatusCodes=OPEN,UPCOMING --region us-east-1 --output json
```

### Load-balancer-type short-circuit

| Attribute | Value | Effect on diagnosis |
|---|---|---|
| `Type` | `application` | **ALB.** L7. Full 5xx diagnostic applies. Access logs include `target_status_code`, `target_processing_time`, `error_reason`. WAF can be associated (561 errors). Health checks are HTTP/HTTPS. |
| `Type` | `network` | **NLB.** L4. Access logs do NOT include `error_reason` or `target_status_code` (connection-level only). No WAF (no 561). Health checks can be TCP (misleading — a TCP handshake succeeds even when the app is broken). Cross-zone off by default. |
| `Scheme` | `internet-facing` | ALB has public IPs. SG allowing 0.0.0.0/0 on ports 80/443 is expected. |
| `Scheme` | `internal` | ALB has private IPs. SG allowing 0.0.0.0/0 on any port is suspicious. |
| `State` | `failed` | ALB is in a failed provisioning state. Output ERROR — do not classify. |

### Target-type short-circuit

| `TargetType` | Effect on diagnosis |
|---|---|
| `instance` | Target registered by EC2 instance ID. Uses the instance's primary private IP. Target SG is the instance's SG. |
| `ip` | Target registered by IP address. Can be outside the VPC (peered VPC, on-prem via Direct Connect). SG rules must use CIDR (not referenced SG) for non-VPC IPs. |
| `alb` | Target is another ALB (nested). Health check is on the parent ALB. Rare — usually a misconfiguration. |
| `lambda` | Target is a Lambda function (ALB-only). No health check — Lambda invocations either succeed or fail. 502 from a Lambda target is a function error (similar to API Gateway Lambda proxy). |

If the input is malformed (missing load balancer ARN, missing target
group ARN, ambiguous error code), emit:

```text
TARGET: <lb-arn or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum the 5xx error
  code (500/502/503/504/561), the load balancer ARN, and the target
  group ARN. Cannot drive a diagnostic tree without the error-code layer.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact 5xx error code
  from the client or ALB access log, (2) the load balancer ARN or name,
  (3) the target group ARN, and (4) for live diagnosis, the time window
  of the failure.
```

## Process — Diagnostic decision tree (apply in error-code order)

The diagnostic tree is error-code-driven. Pick the entry point based on
the observed 5xx code, then walk the layer-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Symptom entry — pick the diagnostic branch

Map the 5xx error code to a branch and jump to that branch's section.

| Error code | Meaning | Branch |
|---|---|---|
| **502 BadGateway** | Target returned invalid response or connection failed | Step 2 |
| **503 ServiceUnavailable** | No healthy targets available | Step 3 |
| **504 GatewayTimeout** | Target did not respond within idle timeout | Step 4 |
| **561 Unauthorized** | WAF blocked the request | Step 5 |
| **500 InternalServerError** | ALB internal failure (rare) | Step 7 |
| Ambiguous / intermittent / mixed codes | Gather access logs first | Step 1b |

### Step 1b: Gather access logs (when the code is ambiguous)

If the operator reports "we're getting 5xx" without a specific code, or
the code varies request-to-request, fetch access logs first.

**ALB access log location:** S3 bucket configured in
`describe-load-balancer-attributes` under `access_logs.s3.bucket`.

```bash
# List recent access log objects
aws s3 ls s3://<bucket>/<prefix>/AWSLogs/<account>/elasticloadbalancing/<region>/ \
  --recursive | sort | tail -20

# Download and analyze recent logs (filter for 5xx)
aws s3 cp s3://<bucket>/<prefix>/AWSLogs/<account>/elasticloadbalancing/<region>/ \
  /tmp/alb-logs/ --recursive
# Parse for 5xx responses
awk '$14 >= 500' /tmp/alb-logs/*.log.gz | zcat | head -50
```

**ALB access log format (space-delimited, key fields):**
```
time elb client:port target:port request_time target_processing_time
response_time elb_status_code target_status_code received_bytes
sent_bytes request "user_agent" ssl_cipher ssl_protocol
target_group_arn trace_id domain_name chosen_cert_arn ...
error_reason
```

The `target_processing_time`, `target_status_code`, and `error_reason`
fields are the highest-signal for 5xx diagnosis.

### Step 2: 502 BadGateway — target returned invalid response

Symptom: client receives `502 BadGateway`. The ALB reached the target
(or tried to) but received no valid HTTP response.

#### 2a: Target returned invalid HTTP or connection failed

```bash
# Target health (are the targets even healthy?)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# If targets are healthy, test the target directly (bypassing the ALB)
# For instance-type targets:
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].PrivateIpAddress'
ssh <bastion> "curl -v http://<target-private-ip>:<target-port>/"

# Check ALB access logs for error_reason
aws s3 ls s3://<bucket>/<prefix>/... --recursive | tail -5
# Download and grep for error_reason on 502 responses
```

**Verdict signals:**
- Access log `error_reason: Target.InvalidResponse` → target returned
  malformed HTTP (non-HTTP bytes, truncated response). **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_INVALID_RESPONSE`. Fix: the target application.
- Access log `error_reason: Target.ConnectionFailed` → connection to
  target refused or reset. If targets are `healthy`, the target port
  closed between health check and request. **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_INVALID_RESPONSE`.
- Target is `unhealthy` with `Target.FailedHealthChecks` → the target
  is failing health checks; the ALB has no healthy target for this
  request. Move to Step 3a (503 diagnosis — same root cause, different
  manifestation).

#### 2b: Target security group does not allow ALB SG

```bash
# Fetch the target's security group (for instance-type targets)
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].SecurityGroups[].GroupId'

# For each target SG, check inbound rules on the target port
aws ec2 describe-security-groups --group-ids <sg-target> --output json | \
  jq '.SecurityGroups[].IpPermissions[]'

# Fetch the ALB's security group
aws elbv2 describe-load-balancers --load-balancer-arns <arn> --output json | \
  jq -r '.LoadBalancers[0].SecurityGroups[]'
```

**Verdict signals:**
- Target SG has NO inbound rule allowing the ALB SG on the target port
  → **ROOT_CAUSE_FOUND**, `LAYER: TARGET_SG_BLOCKED`. The ALB cannot
  reach the target. Fix: add an inbound rule to the target SG allowing
  the ALB SG on the target port.
- Target SG allows a specific IP/CIDR but NOT the ALB SG → if the
  allowed IP is a stale ALB IP, the rule is dead. **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_SG_BLOCKED`. Fix: replace with an ALB-SG-referenced rule.
- Target SG allows the ALB SG on the correct port → SG is not the
  cause. Move to Step 2a (target application issue).

### Step 3: 503 ServiceUnavailable — no healthy targets

Symptom: client receives `503 ServiceUnavailable`. The ALB has no
healthy target in the target group to receive the request.

#### 3a: All targets unhealthy (health check failing)

```bash
# Target health (the smoking gun)
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
# Look for: State: unhealthy, Reason: Target.FailedHealthChecks

# Target group health check configuration
aws elbv2 describe-target-groups --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[0].HealthCheckConfig'
# Key fields: HealthCheckPath, HealthCheckPort, HealthCheckProtocol,
#   Matcher.HttpCode, HealthCheckIntervalSeconds, HealthCheckTimeoutSeconds,
#   HealthyThresholdCount, UnhealthyThresholdCount

# Test the health check endpoint directly on a target
ssh <bastion> "curl -v http://<target-ip>:<target-port><health-check-path>"
```

**Verdict signals:**
- Target health check path returns non-200 (e.g., 404, 500) → the
  health check endpoint itself is broken. **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_HEALTH_CHECK`. Fix: update the health check path to an
  endpoint that returns 200 when healthy, or fix the endpoint.
- `Matcher.HttpCode` does not include the status code the target returns
  (e.g., matcher is `200` but target returns `204` on the health path)
  → **ROOT_CAUSE_FOUND**, `LAYER: TARGET_HEALTH_CHECK`. Fix: update the
  matcher to include the expected code(s) (e.g., `200,204`).
- Health check timeout too short (`HealthCheckTimeoutSeconds` < target
  response time) → health check fails before the target responds.
  **ROOT_CAUSE_FOUND**, `LAYER: TARGET_HEALTH_CHECK`. Fix: increase the
  timeout.
- Health check on wrong port (`HealthCheckPort` != application port)
  → health check hits a port with no listener. **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_HEALTH_CHECK`.

#### 3b: Zero registered targets

```bash
# Target group configuration
aws elbv2 describe-target-groups --target-group-arns <tg-arn> --output json | \
  jq '.TargetGroups[0] | {TargetType, Port, Protocol}'

# Registered targets
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json | \
  jq '.TargetHealthDescriptions'
```

**Verdict signals:**
- `TargetHealthDescriptions` is empty → no targets registered.
  **ROOT_CAUSE_FOUND**, `LAYER: TARGET_NONE_HEALTHY`. Fix: register
  targets (`register-targets`). This is common for newly created target
  groups or after an Auto Scaling group scaled to zero.
- All targets in `unused` state → targets are registered but the target
  group is not attached to any listener rule. **ROOT_CAUSE_FOUND**,
  `LAYER: LISTENER_MISCONFIGURED`. Fix: attach the target group to a
  listener rule.

#### 3c: All targets in draining state

```bash
# Target health
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
# Look for: State: draining

# Deregistration delay
aws elbv2 describe-target-group-attributes --target-group-arn <tg-arn> --output json | \
  jq '.Attributes[] | select(.Key == "deregistration_delay.timeout_seconds")'
```

**Verdict signals:**
- All targets `State: draining` with a long deregistration delay →
  targets were deregistered but are still in the draining window.
  **ROOT_CAUSE_FOUND**, `LAYER: DEREGISTRATION_STUCK`. Fix: register
  new targets, or reduce the deregistration delay if the draining
  window is too long for the deployment pattern.

### Step 4: 504 GatewayTimeout — target did not respond in time

Symptom: client receives `504 GatewayTimeout`. The target did not
respond within the ALB idle timeout.

```bash
# ALB idle timeout
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <arn> --output json | \
  jq '.Attributes[] | select(.Key == "idle_timeout.timeout_seconds")'

# Target response time (from ALB access logs)
# Download logs and check target_processing_time
# Values approaching the idle timeout indicate a slow target

# CloudWatch TargetResponseTime metric
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=<arn-suffix> Name=TargetGroup,Value=<tg-suffix> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Test the target directly (bypassing the ALB)
ssh <bastion> "time curl -v http://<target-ip>:<target-port>/"
```

**Verdict signals:**
- `idle_timeout.timeout_seconds` is 60 (default), target response time
  > 60s → **ROOT_CAUSE_FOUND**, `LAYER: TARGET_TIMEOUT`. Fix: raise the
  idle timeout (if the workload legitimately needs it) or optimize the
  target application.
- Access log `error_reason: Target.Timeout` → confirms the target did
  not respond within the idle timeout. **ROOT_CAUSE_FOUND**,
  `LAYER: TARGET_TIMEOUT`.
- `TargetResponseTime` metric Maximum approaches the idle timeout → the
  target is slow. **ROOT_CAUSE_FOUND**, `LAYER: TARGET_TIMEOUT`.

### Step 5: 561 Unauthorized — WAF blocked the request

Symptom: client receives `561 Unauthorized`. This is a custom error from
WAF blocking the request.

```bash
# Check WAF Web ACLs associated with the ALB
aws wafv2 get-web-acl-for-resource --resource-arn <alb-arn> --output json

# Or list Web ACLs in the region
aws wafv2 list-web-acls --scope REGIONAL --output json

# Fetch WAF logs (if logged to CloudWatch or S3)
aws logs filter-log-events \
  --log-group-name aws-waf-logs-<acl-name> \
  --filter-pattern '"action":"BLOCK"' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'
```

**Verdict signals:**
- WAF Web ACL is associated with the ALB, and WAF logs show BLOCK actions
  for the failing requests → **ROOT_CAUSE_FOUND**, `LAYER: WAF_BLOCKED`.
  Fix: review the WAF rules — a false positive blocking legitimate
  traffic needs the rule adjusted (add an IP exemption, tune the rate
  limit, update the regex pattern).

### Step 6: Listener rule misconfiguration

Symptom: the "wrong" targets are receiving traffic, or a specific path
returns 503 while the root path works. This is a routing issue, not a
target health issue.

```bash
# Listener rules (priority order matters!)
aws elbv2 describe-rules --listener-arn <listener-arn> --output json | \
  jq '.Rules[] | {Priority, Conditions, Actions}'

# Default action on the listener
aws elbv2 describe-listeners --listener-arns <listener-arn> --output json | \
  jq '.Listeners[0].DefaultActions'
```

**Verdict signals:**
- A high-priority rule (low number) matches all paths (`path-pattern: /*`)
  and forwards to the wrong target group → **ROOT_CAUSE_FOUND**,
  `LAYER: LISTENER_MISCONFIGURED`. Fix: adjust rule priorities and
  conditions.
- Default action points to a deleted or empty target group →
  **ROOT_CAUSE_FOUND**, `LAYER: LISTENER_MISCONFIGURED`. Fix: update the
  default action.
- A rule condition mismatches the incoming request (e.g., host-header
  condition does not match) → requests fall through to the default action.
  **ROOT_CAUSE_FOUND**, `LAYER: LISTENER_MISCONFIGURED`.

### Step 7: 500 InternalServerError — rare ALB internal failure

Symptom: client receives `500 InternalServerError`. This is rare and
usually indicates an AWS-side issue.

```bash
# Check AWS Health Dashboard for ELB events
aws health describe-events \
  --filter services=ELASTICLOADBALANCING,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

**Verdict signals:**
- 500 sustained, all targets healthy, no recent change → **ESCALATE**,
  `LAYER: ALB_INTERNAL`. Surface the AWS Health event ARN and open a
  Support case.

### Step 8: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the
symptom clearly indicates an AWS-side incident (region event, sustained
500), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN,
  the load balancer ARN, and the relevant access-log evidence. Recommend
  opening a Support case.
- **NEED_MORE_INFO** — A specific probe requires operator input. List
  the missing pieces (access logs not enabled, target group ARN
  unknown, health check endpoint unclear) and the next probe to run
  once the info is available.

## Output format

```text
TARGET: <lb-arn>/<target-group-arn>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TARGET_HEALTH_CHECK | TARGET_SG_BLOCKED | TARGET_NONE_HEALTHY |
        TARGET_TIMEOUT | TARGET_INVALID_RESPONSE | LISTENER_MISCONFIGURED |
        WAF_BLOCKED | DEREGISTRATION_STUCK | ALB_INTERNAL | UNKNOWN>
EVIDENCE:
  - <observed symptom — error code, error_reason, target state>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <lb-arn>/<tg-arn>. Proceed?
  (yes/no)"
```

### Worked example — 503 from wrong health check path

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-web/abc / target-group/tg-web/def
VERDICT: ROOT_CAUSE_FOUND
REASON: The target group health check path /health returns 404 on all
  targets — the application serves health on /healthz. All targets are
  marked unhealthy, and the ALB has no healthy target for incoming
  requests (Step 3a).
LAYER: TARGET_HEALTH_CHECK
EVIDENCE:
  - Symptom: clients receive 503 ServiceUnavailable on all paths. ALB
    access logs show target_group_arn for tg-web but no
    target_status_code (no target was selected).
  - Probe: aws elbv2 describe-target-health --target-group-arn <tg-web>
    returns all targets State: unhealthy, Reason:
    Target.FailedHealthChecks.
  - Probe: aws elbv2 describe-target-groups --target-group-arns <tg-web>
    returns HealthCheckPath: /health, Matcher.HttpCode: 200.
  - Probe: ssh <bastion> "curl -v http://<target-ip>:8080/health"
    returns HTTP/1.1 404 Not Found. "curl http://<target-ip>:8080/healthz"
    returns HTTP/1.1 200 OK.
  - Passing: target SG allows ALB SG on port 8080; ALB idle timeout is
    60s; listener default action points to tg-web; no WAF associated.
REMEDIATION:
  1. Update the health check path to /healthz:
     aws elbv2 modify-target-group --target-group-arn <tg-web>
       --health-check-path /healthz --profile <p>
  2. Wait for healthy_threshold_count consecutive successful checks
     (default: 3-5 checks at HealthCheckIntervalSeconds).
  3. Verify: describe-target-health shows State: healthy for all
     targets; clients no longer see 503.
CONFIRM: Before modifying the target group, emit and await:
  "CONFIRM: About to modify-target-group on tg-web (health-check-path
   /health → /healthz). Proceed? (yes/no)"
```

### Worked example — 502 from target SG not allowing ALB SG

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-api/ghi / target-group/tg-api/jkl
VERDICT: ROOT_CAUSE_FOUND
REASON: The target security group sg-target-api has no inbound rule
  allowing the ALB security group sg-alb-prod on port 443 — the ALB
  cannot establish a connection to the targets (Step 2b).
LAYER: TARGET_SG_BLOCKED
EVIDENCE:
  - Symptom: clients receive 502 BadGateway. ALB access logs show
    error_reason: Target.ConnectionFailed for all requests.
  - Probe: aws elbv2 describe-target-health shows all targets State:
    healthy (health check is on a different port that IS allowed by
    the SG — port 80, while the target group serves on 443).
  - Probe: aws ec2 describe-security-groups --group-ids sg-target-api
    returns inbound rules allowing tcp/80 from sg-alb-prod but NO rule
    for tcp/443.
  - Probe: aws elbv2 describe-target-groups returns Port: 443 for
    tg-api (the target group forwards on 443, not 80).
  - Passing: health check passes on port 80 (traffic from sg-alb-prod
    on port 80 is allowed); targets are healthy; ALB idle timeout is
    60s; listener rule correctly points to tg-api.
REMEDIATION:
  1. Add an inbound rule to sg-target-api allowing the ALB SG on port
     443:
     aws ec2 authorize-security-group-ingress --group-id sg-target-api
       --protocol tcp --port 443 --source-security-group-id sg-alb-prod
       --profile <p>
  2. Verify: curl from the ALB subnet to the target on 443 succeeds;
     clients no longer see 502.
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-target-api
   for sg-alb-prod on tcp/443. Proceed? (yes/no)"
```

### Worked example — 504 from target exceeding idle timeout

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-reports/mno / target-group/tg-reports/pqr
VERDICT: ROOT_CAUSE_FOUND
REASON: The report-generation endpoint takes 75-90 seconds to respond,
  exceeding the ALB idle timeout of 60 seconds. The ALB returns 504 at
  60s while the target continues processing (Step 4).
LAYER: TARGET_TIMEOUT
EVIDENCE:
  - Symptom: clients receive 504 GatewayTimeout on POST /reports/generate
    after exactly 60 seconds.
  - Probe: aws elbv2 describe-load-balancer-attributes returns
    idle_timeout.timeout_seconds: 60.
  - Probe: ALB access logs show target_processing_time: 60.0 and
    error_reason: Target.Timeout for the failing requests.
  - Probe: CloudWatch TargetResponseTime metric shows Maximum 60.0s
    (capped — the ALB closes at 60s even though the target continues).
  - Probe: ssh <bastion> "time curl -X POST
    http://<target-ip>:8080/reports/generate -d '@test.json'"
    returns the response in 82 seconds (the target is slow but succeeds
    when given time).
  - Passing: targets are healthy; target SG allows ALB SG on 8080;
    listener rule correctly points to tg-reports.
REMEDIATION:
  1. Raise the ALB idle timeout to 120s (verify the target can finish
     within 120s):
     aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn>
       --attributes Key=idle_timeout.timeout_seconds,Value=120
       --profile <p>
  2. Alternatively, migrate the report-generation endpoint to an async
     pattern (POST returns 202 with a job ID; client polls for status).
     This is preferred for endpoints that take > 60s.
  3. Verify: POST /reports/generate returns 200 within 120s.
CONFIRM: Before modifying the ALB attributes, emit and await:
  "CONFIRM: About to modify-load-balancer-attributes on <arn>
   (idle_timeout 60 → 120). Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches the
  symptom. "Must be the targets" without running `describe-target-health`
  or checking access logs erodes operator trust.

- NEVER confuse 502 and 503. A 502 means the ALB reached the target but
  got an invalid response (or connection failed). A 503 means no healthy
  target was available (the ALB never sent the request to a target).
  Probing target health for a 502 when all targets are healthy wastes
  the incident window — the target application is the cause, not target
  selection.

- NEVER assume a `healthy` target is actually serving the application
  correctly. A health check on `/health` returning 200 does NOT mean
  the application works on its real endpoints. A target can be `healthy`
  while returning 500 to clients — the ALB routes to it, and clients
  see the 500. Always test the actual endpoint, not just the health
  check path.

- NEVER trust an NLB `healthy` status without verifying
  `health_check.type`. The default TCP health check succeeds on a bare
  handshake — an app returning 500s is marked `healthy`. For HTTP/HTTPS
  targets behind an NLB, require `health_check.type = HTTP/HTTPS` with
  a real `path`. A TCP check on an HTTP target is the most common cause
  of "healthy but broken" NLB incidents.

- NEVER configure a target SG rule with the ALB's IP address. ALB IPs
  change when the ALB scales. Use the ALB security group ID as the
  source — this is stable across scaling events.

- NEVER assume access logs are delivered just because
  `access_logs.s3.enabled` is `true`. The S3 bucket policy MUST grant
  `elasticloadbalancing.amazonaws.com` write access with
  `aws:SourceAccount` condition. A misconfigured bucket policy causes
  logs to silently fail. Verify with `aws s3 ls` on the prefix after
  5-10 minutes.

- NEVER recommend raising the ALB idle timeout without verifying the
  target can actually finish within the new timeout. A target that takes
  300s will still 504 with a 120s timeout. For long-running requests,
  migrate to an async pattern (202 + polling).

- NEVER forget that ALB cross-zone load balancing is ALWAYS ON. It cannot
  be disabled. Do not flag an ALB for cross-zone issues. Only NLB has
  the toggle (off by default).

- NEVER treat 561 as a backend error. 561 is a WAF block — the request
  never reached the target. Check the WAF Web ACL, not the target health.

- NEVER conflate deregistration delay with unhealthy targets. Targets in
  `draining` state are NOT unhealthy — they were deliberately deregistered
  and are serving in-flight requests. The fix is to register new targets,
  not to "fix" the draining targets.

- NEVER assume the listener default action points to the right target
  group. A misconfigured default action (pointing to an empty or deleted
  target group) produces 503 for any request that does not match a
  specific rule. Always verify `DefaultActions` in `describe-listeners`.

- NEVER evaluate listener rules out of priority order. Rules are
  evaluated lowest-number-first. A low-priority rule with a broad
  condition (`path-pattern: /*`) shadows higher-priority rules. Always
  list rules sorted by priority when diagnosing routing issues.

- NEVER recommend deleting a target group or load balancer as
  remediation. These resources have listener rules, Auto Scaling groups,
  and DNS records that depend on them. Remediation is always to fix the
  targets, health check, or security group — not to remove the LB.

- NEVER ignore the health check grace period for new deployments. New
  targets start in `initial` state and must pass
  `healthy_threshold_count` checks before becoming `healthy`. If all
  old targets were deregistered simultaneously, the ALB has no healthy
  targets during this window. Use a blue-green or rolling deployment.

- NEVER assume an IP-type target in a peered VPC uses a referenced SG.
  IP-type targets outside the VPC (peered VPC, on-prem) cannot use
  referenced SG rules — they require CIDR-based rules. A target SG rule
  referencing the ALB SG fails for a cross-VPC IP target.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-target-group`, `modify-load-balancer-attributes`,
  `authorize-security-group-ingress`, `modify-listener`,
  `modify-rule`), emit and await operator approval. Do NOT execute the
  CLI until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is read-only
  (`describe-*`, `aws s3 ls/cp`, `get-metric-statistics`, `curl`). Do
  not perform state-changing operations as diagnostic probes.

- **Health check path changes affect ALL targets.** Modifying
  `HealthCheckPath` causes all targets to be re-evaluated. If the new
  path is wrong, ALL targets go `unhealthy` simultaneously, producing a
  full outage. Test the new path on one target first.

- **Idle timeout changes apply immediately** and affect all connections.
  Raising the timeout holds connections longer (more memory on targets);
  lowering it may cut off slow legitimate requests.

- **Security group changes can affect multiple targets.** A target SG
  rule change applies to all instances using that SG. Verify the scope
  before modifying.

- **Listener rule priority changes are live immediately.** Reordering
  rules affects traffic routing instantly. Test in a staging environment
  first.

- **Access log enablement is non-disruptive** but requires a valid S3
  bucket with the correct policy. Verify the bucket exists and has the
  ELB write policy before enabling.

## Remediation guidance

### For TARGET_HEALTH_CHECK — wrong health check configuration

1. Identify the correct health check endpoint (an application route that
   returns 200 when healthy):
   ```bash
   ssh <bastion> "curl -v http://<target-ip>:<port><candidate-path>"
   # Test multiple paths: /health, /healthz, /ready, /status
   ```
2. Update the health check configuration:
   ```bash
   aws elbv2 modify-target-group --target-group-arn <tg-arn> \
     --health-check-path /healthz \
     --matcher HttpCode=200,204 \
     --profile <p>
   ```
3. Wait for `healthy_threshold_count` consecutive successful checks.
4. Verify: `describe-target-health` shows `healthy`.

### For TARGET_SG_BLOCKED — target SG does not allow ALB SG

1. Add an inbound rule to the target SG:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-target> \
     --protocol tcp --port <target-port> \
     --source-security-group-id <sg-alb> --profile <p>
   ```
2. Verify: `curl` from the ALB subnet to the target on the target port.

### For TARGET_NONE_HEALTHY — no registered targets

1. Register targets:
   ```bash
   aws elbv2 register-targets --target-group-arn <tg-arn> \
     --targets Id=<i-id>,Port=<port> --profile <p>
   ```
2. Wait for health checks to pass.
3. Verify: `describe-target-health` shows `healthy`.

### For TARGET_TIMEOUT — target exceeding idle timeout

1. Raise the idle timeout (if the workload legitimately needs it):
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=idle_timeout.timeout_seconds,Value=120 \
     --profile <p>
   ```
2. Or migrate to an async pattern for long-running requests.

### For TARGET_INVALID_RESPONSE — target returning malformed HTTP

1. Test the target directly to identify the malformed response:
   ```bash
   ssh <bastion> "curl -v http://<target-ip>:<port>/"
   ```
2. Fix the target application (HTTP server crash, wrong port, SSL
   configuration).
3. Verify: the target returns a valid HTTP response.

### For DEREGISTRATION_STUCK — targets stuck in draining

1. Register new targets to replace the draining ones.
2. Optionally reduce the deregistration delay:
   ```bash
   aws elbv2 modify-target-group-attributes --target-group-arn <tg-arn> \
     --attributes Key=deregistration_delay.timeout_seconds,Value=30 \
     --profile <p>
   ```

### For WAF_BLOCKED — WAF false positive

1. Identify the blocking rule in WAF logs.
2. Add an exemption or tune the rule:
   ```bash
   aws wafv2 update-web-acl --web-acl-arn <acl-arn> \
     --rules file://updated-rules.json --profile <p>
   ```

### For LISTENER_MISCONFIGURED — wrong target group or priority

1. Update the listener rule:
   ```bash
   aws elbv2 modify-rule --rule-arn <rule-arn> \
     --actions Type=forward,TargetGroupArn=<correct-tg-arn> --profile <p>
   ```

### For ESCALATE — AWS-side incident

1. Surface the AWS Health event ARN and load balancer ARN.
2. Open a Support case with the time window and access-log evidence.

## Domain

AWS CloudOps / ELBv2 Load Balancer Diagnostics, Target Health Analysis,
Security Group Verification, and Incident Diagnosis.

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

## AWS documentation

- **Elastic Load Balancing User Guide** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html
- **Target groups** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- **Target health for Application Load Balancers** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- **Access logs for Application Load Balancers** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
- **ALB troubleshooting** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/ts-elb-error-codes.html
- **ELB Security** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/security.html
- **AWS CLI ELBv2 reference** — https://docs.aws.amazon.com/cli/latest/reference/elbv2/
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
