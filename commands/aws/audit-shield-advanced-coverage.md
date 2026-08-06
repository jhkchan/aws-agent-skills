---
description: Audit AWS Shield Advanced DDoS coverage posture — protected-resource coverage (CloudFront/Route 53 auto-protection, ALB/NLB/CLB/EIP/EC2 explicit protection), DRT role and log-bucket access, health-based detection, proactive engagement, and WAF L7 integration.
nl_triggers:
  - "audit Shield Advanced coverage"
  - "is my ALB protected by Shield Advanced"
  - "check DRT access"
  - "Shield Advanced DRT access"
  - "is proactive engagement enabled"
  - "Shield Advanced health-based detection"
  - "which resources are DDoS protected"
  - "Shield Advanced subscription state"
  - "DDoS response team access"
  - "harden DDoS posture"
  - "Shield Advanced coverage gaps"
  - "is my Elastic IP protected"
  - "CloudFront auto-protection"
  - "Shield Advanced WAF integration"
  - "DDoS posture review"
routes_to: shield-advanced-coverage-auditor
---

# /aws:audit-shield-advanced-coverage

Activate the `shield-advanced-coverage-auditor` skill and audit an AWS
Shield Advanced configuration for DDoS coverage posture.

## What it does

Reads a Shield Advanced configuration snapshot and applies the ordered
classification logic:

1. Subscription gate — `SubscriptionState: INACTIVE` means zero enhanced
   protections (UNPROTECTED).
2. Resource coverage — CloudFront/Route 53 are AUTO-PROTECTED (do NOT flag
   absence from Protections list); ALB/NLB/CLB/EIP need explicit
   `CreateProtection`.
3. DRT access — missing DRT role = NO_DRT_ACCESS; missing log bucket only
   = CONFIG_GAP (partial DRT, blind to logs).
4. Health-based detection — per-Protection Route 53 health check; empty
   HealthCheckIds = CONFIG_GAP (L7 blind, no cost-protection credits).
5. Proactive engagement — DISABLED or enabled without contacts =
   CONFIG_GAP.
6. WAF L7 integration — ALB with Shield but no WAF Web ACL = CONFIG_GAP
   (L3/L4 only, DRT cannot inject rate-based rules).
7. Aggregation — worst finding wins (UNPROTECTED > NO_DRT_ACCESS >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per account/scope:

```text
SCOPE: <account-id (region)>
VERDICT: UNPROTECTED | NO_DRT_ACCESS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [UNPROTECTED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Shield Advanced configuration snapshot and ask any of:

- "audit Shield Advanced coverage"
- "is my ALB protected by Shield Advanced?"
- "check DRT access"
- "is proactive engagement enabled?"
- "which resources are DDoS protected?"
- "Shield Advanced coverage gaps"

A bare account-id + any audit verb ("audit DDoS posture", "check Shield
coverage") also routes here via the orchestrator.

## Inputs

- A Shield Advanced configuration snapshot (text or JSON), pasted inline
  or referenced by file path.
- Key fields: `SubscriptionState`, internet-facing resource inventory
  (CloudFront distributions, Route 53 zones, ALB/NLB/CLB ARNs, EIP
  allocations, EC2 instances with EIPs), `Protections` (from
  ListProtections), DRT access config (RoleArn, LogBuckets from
  DescribeDRTAccess), `ProactiveEngagement` state,
  `EmergencyContactList`, WAF Web ACL associations.
- For multi-region audits: each region is audited independently (ALB/NLB/
  CLB/EIP protections are regional; CloudFront/Route 53 are global).

## Outputs

- One VERDICT block per account/scope (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: create Protection, associate DRT role/log bucket,
  associate health check, enable proactive engagement, associate WAF Web
  ACL.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for DDoS protection coverage).
- `/aws:audit-cloudfront-distribution` for CloudFront edge-security
  analysis (TLS, OAC, WAF, logging).
- `/aws:audit-wafv2-web-acl` for WAF rule-level analysis when a Web ACL is
  associated but rule quality is in question.
- `/aws:audit-elbv2-load-balancer` for ALB/NLB listener and security-group
  analysis.
