---
description: Diagnose ALB or NLB 5xx errors (500, 502, 503, 504, 561) through an error-code-driven diagnostic tree — identifies target health failures, SG misconfigurations, idle timeout exceeded, deregistration issues, and emits ROOT_CAUSE_FOUND with the specific failure layer.
nl_triggers:
  - "ALB 5xx error"
  - "ALB 502 BadGateway"
  - "ALB 503 ServiceUnavailable"
  - "ALB 504 GatewayTimeout"
  - "ALB 561 Unauthorized"
  - "ALB 500 InternalServerError"
  - "NLB 5xx error"
  - "target unhealthy"
  - "no healthy targets"
  - "target group health check failed"
  - "Target.FailedHealthChecks"
  - "Target.ConnectionFailed"
  - "Target.InvalidResponse"
  - "Target.Timeout"
  - "ALB access logs 5xx"
  - "target security group blocked"
  - "deregistration draining stuck"
  - "WAF blocked request ALB"
  - "troubleshoot ALB 5xx"
  - "troubleshoot load balancer 5xx"
  - "ALB returning errors"
routes_to: alb-5xx-troubleshooter
---

# /aws:troubleshoot-alb-5xx

Activate the `alb-5xx-troubleshooter` skill and diagnose an ALB or NLB
5xx error through the error-code-driven diagnostic tree.

## What it does

Reads a symptom description (5xx error code, observed pattern, failing
target group) plus the load balancer and target group metadata, then
walks the error-code-specific diagnostic tree to a root cause with
positive evidence:

1. **Pre-flight** — load balancer type (ALB vs NLB), scheme, target
   type (instance, ip, lambda), listener configuration. Short-circuits
   on missing context (NEED_MORE_INFO).
2. **Symptom entry** — map the 5xx code to a branch:
   - **502** → target invalid response, target SG blocking ALB,
     connection failed.
   - **503** → all targets unhealthy (health check config wrong),
     targets draining, zero registered targets, listener default action
     misconfigured.
   - **504** → target exceeding idle timeout (60s default).
   - **561** → WAF blocked the request (false positive or rate rule).
   - **500** → ALB internal error (rare); check AWS Health Dashboard.
3. **Layer-specific probes** — `describe-target-health` (the
   highest-signal command), `describe-target-groups` (health check
   config), ALB access logs in S3 (`error_reason`, `target_processing_time`,
   `target_status_code`), `describe-security-groups` (target SG vs ALB
   SG), `describe-rules` (listener priorities), WAF logs, CloudWatch
   `HTTPCode_ELB_5XX_Count` and `TargetResponseTime`.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   symptom), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side incident; surface AWS Health event ARN).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "ALB returning 502 BadGateway"
- "503 ServiceUnavailable — no healthy targets"
- "504 GatewayTimeout on my ALB"
- "ALB 561 errors from WAF"
- "target group all unhealthy"
- "ALB access logs show error_reason"
- "troubleshoot load balancer 5xx errors"

A bare load balancer ARN or name + any 5xx code ("prod-web ALB is
returning 503", "tg-api has unhealthy targets") also routes here via
the orchestrator.

## Inputs

- Symptom description: 5xx error code (500/502/503/504/561), observed
  pattern, intermittent vs persistent, recent deployment or config change.
- Load balancer and target group metadata: type (ALB/NLB), target type,
  health check configuration, target health states, security groups,
  listener rules, ALB attributes (idle timeout, deregistration delay).
- For live-account diagnosis: load balancer ARN or name, target group
  ARN, time window of the failure. The skill uses `describe-target-health`,
  `describe-target-groups`, `describe-listeners`, `describe-rules`,
  `describe-load-balancer-attributes`, `describe-security-groups`,
  `aws s3 cp` (access logs), `get-metric-statistics`.

## Outputs

- One diagnostic block per target load balancer / target group.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: health check path update, SG rule addition,
  target registration, idle timeout adjustment, WAF rule tuning, or
  AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for ALB/NLB 5xx).
- `/aws:audit-elbv2-load-balancer` for configuration posture audits on
  the same load balancer (TLS policy, access logs, SG exposure,
  deletion protection).
- `/aws:audit-ec2-security-groups` for security-group exposure audits
  on the target side.
