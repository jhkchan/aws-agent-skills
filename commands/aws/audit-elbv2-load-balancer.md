---
description: Audit an ELBv2 load balancer (ALB/NLB) for insecure TLS listener policies, disabled access logs, permissive security groups, idle targets, cross-zone gaps, and missing deletion protection.
nl_triggers:
  - "audit this load balancer"
  - "check ALB TLS policy"
  - "is my ALB secure"
  - "is my NLB secure"
  - "load balancer access logs disabled"
  - "permissive security group ALB"
  - "idle load balancer no targets"
  - "cross-zone load balancing NLB"
  - "deletion protection load balancer"
  - "ELBSecurityPolicy TLS 1.0"
  - "ELBSecurityPolicy-2016-08"
  - "ALB listener cipher"
  - "NLB TLS listener"
  - "hardening load balancer"
  - "ALB security group too open"
routes_to: elbv2-load-balancer-auditor
---

# /aws:audit-elbv2-load-balancer

Activate the `elbv2-load-balancer-auditor` skill and audit one or more ELBv2
load balancer configurations for security exposure.

## What it does

Reads an ELBv2 load balancer configuration (type, scheme, listeners with
protocols/SSL policies, security group rules, target group health, attributes)
and applies the ordered classification logic:

1. Listener TLS security — TLS 1.0/1.1 in SslPolicy, weak ciphers, HTTP-only
   with no HTTPS redirect → INSECURE_LISTENER.
2. Security group exposure — all-ports-open to 0.0.0.0/0, non-listener ports
   exposed, internal LB open to internet → PERMISSIVE_SG.
3. Access logs — AccessLogsEnabled false → NO_ACCESS_LOGS.
4. Target health — zero registered targets or all unhealthy → IDLE.
5. Configuration gaps — NLB cross-zone off, deletion protection off →
   CONFIG_GAP.
6. Aggregation — worst finding wins by priority
   (INSECURE_LISTENER > PERMISSIVE_SG > NO_ACCESS_LOGS > IDLE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per load balancer:

```text
LB: <arn>
VERDICT: INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an ALB or NLB configuration and ask any of:

- "audit this load balancer"
- "check my ALB TLS policy"
- "is this load balancer secure?"
- "is access logging enabled on my ALB?"
- "is my security group too open?"
- "why is my load balancer returning 502?"
- "should I enable cross-zone on my NLB?"
- "is deletion protection on?"

A bare load balancer ARN + any audit verb ("audit this ALB", "check NLB
config") also routes here via the orchestrator.

## Inputs

- Load balancer type (application / network), scheme (internet-facing /
  internal), state.
- Listeners: protocol (HTTP/HTTPS/TCP/TLS), port, SslPolicy (for TLS
  listeners), default action (forward/redirect).
- Security group inbound rules (port range, source CIDR).
- Target group target health (registered count, health status).
- Load balancer attributes: access_logs.s3.enabled,
  load_balancing.cross_zone.enabled, deletion_protection.enabled.

## Outputs

- One VERDICT block per load balancer (multiple findings aggregate to the
  worst verdict by priority).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation with CLI commands: modify-listener SslPolicy,
  revoke/authorize security-group-ingress, modify-load-balancer-attributes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for ELBv2 load balancer security).
- `/aws:audit-ec2-security-groups` for deeper security group analysis.
- `/aws:audit-wafv2-web-acl` for WAFv2 Web ACL posture on ALB.
