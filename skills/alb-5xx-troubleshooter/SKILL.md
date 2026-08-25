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

Full diagnostic mindset (the ALB is the messenger, not the cause): [references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

The four senior-engineer behaviours (5xx code tells WHERE, health check config is the top root cause, SG rules are bidirectional, access logs are the forensic trail): [references/advanced-patterns.md](references/advanced-patterns.md).

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
| Need full probes for any Step | Reference | `references/diagnostic-commands.md` |
| Need more worked examples | Reference | `references/worked-examples.md` |
| Need per-layer fix commands | Reference | `references/error-handling.md` |
| Need Step 0 gotchas in full | Reference | `references/advanced-patterns.md` |

## Pre-flight: load balancer type and gather-info gate

Before running code-specific probes, gather the canonical load balancer,
listener, target group, and target health metadata. Misidentifying the
load balancer type (ALB vs NLB) or the target type (instance vs ip vs
lambda) produces false root causes.

### Account-wide pre-flight commands

Account-wide pre-flight commands (describe-load-balancers, -listeners, -rules, -target-groups, -target-health, attributes, SGs, CloudWatch 5xx metrics, AWS Health): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

NEED_MORE_INFO re-prompt template for malformed/missing input: [references/worked-examples.md](references/worked-examples.md).

## Process — Diagnostic decision tree (apply in error-code order)

The diagnostic tree is error-code-driven. Pick the entry point based on
the observed 5xx code, then walk the layer-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

The 13 non-obvious behaviours (shallow /health checks, NLB TCP false-healthy, ALB-SG-vs-IP rules, draining window, S3 log delivery, error_reason semantics, idle-timeout scope, NLB cross-zone default, rule priority order, instance-ID registration, WAF 561, Lambda 502, grace period, AZ reachability): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Access-log location (access_logs.s3.bucket), fetch/parse commands, and the space-delimited field format (target_processing_time, target_status_code, error_reason): [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 2: 502 BadGateway — target returned invalid response

Symptom: client receives `502 BadGateway`. The ALB reached the target
(or tried to) but received no valid HTTP response.

#### 2a: Target returned invalid HTTP or connection failed

Probes (describe-target-health, direct curl on target, access-log error_reason): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (target SG inbound rules vs ALB SG on target port): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (target health reason, HealthCheckConfig fields, direct curl of the health path): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (TargetType + registered target list): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (draining state + deregistration_delay.timeout_seconds): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- All targets `State: draining` with a long deregistration delay →
  targets were deregistered but are still in the draining window.
  **ROOT_CAUSE_FOUND**, `LAYER: DEREGISTRATION_STUCK`. Fix: register
  new targets, or reduce the deregistration delay if the draining
  window is too long for the deployment pattern.

### Step 4: 504 GatewayTimeout — target did not respond in time

Symptom: client receives `504 GatewayTimeout`. The target did not
respond within the ALB idle timeout.

Probes (idle_timeout.timeout_seconds, access-log target_processing_time, TargetResponseTime metric, direct timed curl): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (get-web-acl-for-resource, list-web-acls, WAF BLOCK log filter): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (describe-rules priority order, listener DefaultActions): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe (aws health describe-events for ELB): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full worked example (502, healthy targets, SG missing tcp/443 from ALB SG; LAYER: TARGET_SG_BLOCKED): [references/worked-examples.md](references/worked-examples.md).

### Worked example — 504 from target exceeding idle timeout

Full worked example (504 at exactly 60s, Target.Timeout; LAYER: TARGET_TIMEOUT): [references/worked-examples.md](references/worked-examples.md).

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

Per-LAYER fix playbooks (TARGET_HEALTH_CHECK, TARGET_SG_BLOCKED, TARGET_NONE_HEALTHY, TARGET_TIMEOUT, TARGET_INVALID_RESPONSE, DEREGISTRATION_STUCK, WAF_BLOCKED, LISTENER_MISCONFIGURED, ESCALATE): [references/error-handling.md](references/error-handling.md).

## Domain

AWS CloudOps / ELBv2 Load Balancer Diagnostics, Target Health Analysis,
Security Group Verification, and Incident Diagnosis.

## Recent AWS features (2024-2026)

Full feature list with dates: [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — account-wide pre-flight gather-info gate, Step 1b access-log fetch, and every step's probe commands (2a-7)
- [Worked examples](references/worked-examples.md) — 502 from target SG not allowing ALB SG, 504 from target exceeding idle timeout, NEED_MORE_INFO re-prompt
- [Error handling](references/error-handling.md) — per-LAYER remediation guidance with fix and verify commands
- [Advanced patterns](references/advanced-patterns.md) — diagnostic mindset, philosophy, Step 0 non-obvious behaviours, recent AWS features
- [Target health reference](references/target-health-reference.md) — error-code catalog, reason codes, access-log fields, SG evaluation, metrics

## AWS documentation

- **Elastic Load Balancing User Guide** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html
- **Target groups** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- **Target health for Application Load Balancers** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- **Access logs for Application Load Balancers** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
- **ALB troubleshooting** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/ts-elb-error-codes.html
- **ELB Security** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/security.html
- **AWS CLI ELBv2 reference** — https://docs.aws.amazon.com/cli/latest/reference/elbv2/
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
