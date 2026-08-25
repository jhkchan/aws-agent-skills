# Error Handling — Route 53 Health Check Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Malformed input — INSUFFICIENT_DATA re-prompt

If input is malformed (missing HealthCheckId, absent symptom
description), emit:

```text
TARGET: <health-check-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (health check status, failover behaviour) and the
  HealthCheckId or domain name.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the HealthCheckId or
  domain name, (2) the observed health check status (healthy /
  unhealthy / flapping), (3) the routing policy and record TTL,
  and (4) the failover behaviour (not triggering, slow, wrong
  endpoint served).
```
