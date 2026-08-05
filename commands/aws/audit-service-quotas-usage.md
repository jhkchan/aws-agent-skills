---
description: Audit AWS Service Quotas for utilization, approaching limits (>=80%), CloudWatch alarm coverage, applied vs default drift, and quota increase request history.
nl_triggers:
  - "audit service quotas"
  - "check quota utilization"
  - "approaching service limit"
  - "quota increase request"
  - "cloudwatch alarm on quota"
  - "applied vs default quota"
  - "AWS/Usage metric"
  - "service limits audit"
  - "quota headroom"
  - "will I hit my quota"
  - "quota monitoring gap"
  - "denied quota increase"
routes_to: service-quotas-usage-auditor
---

# /aws:audit-service-quotas-usage

Activate the `service-quotas-usage-auditor` skill and audit one or more
Service Quotas snapshots for utilization risk, alarm coverage, and
quota-increase-request health.

## What it does

Reads a Service Quotas snapshot (quota code, service code, applied value,
default value, UsageMetric, utilization, increase request history,
CloudWatch alarm state) and applies the ordered classification logic:

1. Utilization threshold — >= 80% of applied quota is APPROACHING_LIMIT
   (operational risk dominates all other findings).
2. Structural config gap — no UsageMetric (cannot auto-monitor),
   Adjustable: false at high utilization, DENIED increase request,
   or adjustable quota stuck at default with >= 50% utilization.
3. Alarm coverage — has UsageMetric, utilization < 80%, but no
   CloudWatch alarm configured → NO_ALARM.
4. Aggregation — worst finding wins (APPROACHING_LIMIT > CONFIG_GAP >
   NO_ALARM > OK).

Emits a deterministic VERDICT per quota:

```text
QUOTA: <quota-code> (<quota-name>)
SERVICE: <service-code>
VERDICT: APPROACHING_LIMIT | NO_ALARM | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
UTILIZATION: <current>/<applied> (<pct>%) [default: <default>] [unit: <unit>]
FINDINGS:
  - [APPROACHING_LIMIT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

## When to invoke

Paste a Service Quotas snapshot and ask any of:

- "audit my service quotas"
- "are we approaching any limits?"
- "check quota utilization for EC2"
- "do we have CloudWatch alarms on our quotas?"
- "was our quota increase denied?"
- "is the pending increase in effect yet?"
- "what quotas have no monitoring?"

A bare service code (e.g., `ec2`, `vpc`, `lambda`) plus any audit verb
("audit quotas", "check limits") also routes here.

## Inputs

- A Service Quotas snapshot: quota code, service code, applied value,
  default value, Unit, Adjustable, GlobalQuota, UsageMetric (if any),
  current utilization, CloudWatch alarm state, increase request history.
- For multi-service sweeps: provide snapshots per quota. The skill
  processes each independently and emits a VERDICT block per quota.
- For live-account audits: the skill guides the operator through
  `aws service-quotas list-service-quotas`, `get-service-quota`,
  `get-aws-default-service-quota`,
  `list-requested-service-quota-change-history`, and
  `aws cloudwatch describe-alarms`.

## Outputs

- One VERDICT block per quota (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: request increase, create CloudWatch alarm with
  exact dimensions, open support case, redistribute across regions.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Service Quotas capacity management).
- `/aws:audit-trustedadvisor-checks` for the legacy service-limits checks
  (deprecated subset — Service Quotas + AWS/Usage is the modern path).
