---
description: Diagnoses Amazon Route 53 health check and DNS failover failures through a ten-category diagnostic tree (endpoint health, certificate mismatch, calculated logic, interval/threshold, routing policy, DNS resolution, NS delegation, health check regions, alarm-based) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "Route 53 health check unhealthy"
  - "Route 53 health check failure"
  - "DNS failover not working"
  - "Route 53 failover not triggering"
  - "DNS failover active-passive"
  - "calculated health check AND OR NOT"
  - "Route 53 endpoint health check"
  - "Route 53 HTTP health check"
  - "Route 53 HTTPS health check"
  - "Route 53 TCP health check"
  - "health check failure threshold"
  - "consecutive health check failures"
  - "Route 53 health check interval"
  - "DNS failover weighted routing"
  - "DNS failover latency-based routing"
  - "Route 53 geolocation failover"
  - "health check regions Route 53"
  - "Route 53 caller IP"
  - "CloudWatch alarm-based health check"
  - "DNS resolution NS delegation"
  - "hosted zone delegation issue"
  - "glue record propagation"
  - "troubleshoot Route 53 health check"
  - "Route 53 certificate mismatch"
  - "health check cert validation"
routes_to: route53-health-check-troubleshooter
---

# /aws:troubleshoot-route53-health-check

Activate the `route53-health-check-troubleshooter` skill and diagnose
an Amazon Route 53 health check or DNS failover failure through the
ten-category diagnostic tree.

## What it does

Reads a symptom description (health check status, observed DNS
response, failover behaviour) plus the health check and routing
configuration, then walks the symptom-driven diagnostic tree to a root
cause with positive evidence:

1. **Pre-flight** — health check config (type, endpoint, interval,
   threshold), health check status (per-region), record sets (routing
   policy, health check association, TTL), CloudWatch alarm state.
   Short-circuits on wrong health check type, unreachable private IP,
   or missing health check association.
2. **Symptom entry** — map the symptom to one of: endpoint health
   failure (unreachable from health checkers), certificate mismatch
   on HTTPS, calculated health check logic error, failover not
   triggering (routing policy / threshold), DNS stale record (TTL
   caching), health check region variation, CloudWatch alarm-based
   ambiguity, NS delegation failure.
3. **Layer-specific probes** —
   - Endpoint health: `get-health-check` type/port/path/IP;
     `get-health-check-status` per-region; SG/firewall rules for
     health checker IPs; protocol mismatch (HTTP redirect, wrong port,
     wrong path).
   - Certificate mismatch: FQDN vs cert SAN; EnableSNI; `openssl
     s_client` for cert details; expired or self-signed cert.
   - Calculated HC: `get-health-check` Type: CALCULATED,
     ChildHealthChecks, Inverted flag; child health check statuses.
   - Failover routing: `list-resource-record-sets` routing policy,
     HealthCheckId association on each record; FAILOVER primary/
     secondary config; WEIGHTED/LATENCY/GEOLOCATION per-record HC.
   - DNS resolution: `dig` authoritative vs public resolver; TTL on
     the record; stale record after failover.
   - NS delegation: `dig NS` parent vs hosted zone; glue records;
     propagation status.
   - Health check regions: per-region breakdown in
     `get-health-check-status`; geographic IP blocking.
   - Alarm-based HC: `describe-alarms` state (OK/ALARM/
     INSUFFICIENT_DATA); alarm period, evaluation periods, datapoints
     to alarm, threshold, comparison operator.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (critical config missing).

Emits a deterministic diagnostic block per target:

```text
TARGET: <health-check-id / domain-name / record-set>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ENDPOINT_HEALTH | PROTOCOL_MISMATCH | CERTIFICATE_MISMATCH |
        CALCULATED_HC_LOGIC | HC_INTERVAL_THRESHOLD |
        DNS_FAILOVER_ROUTING | DNS_RESOLUTION | NS_DELEGATION |
        HC_REGION_SELECTION | ALARM_BASED_HC | LATENCY_MEASUREMENT |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — health check status / failover behaviour>
  - <failing probe — command and output confirming the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "Route 53 health check is unhealthy"
- "DNS failover not triggering"
- "HTTPS health check cert mismatch"
- "Calculated health check reporting wrong status"
- "DNS still returns old record after failover"
- "Health check unhealthy but endpoint works from VPC"
- "CloudWatch alarm-based health check not triggering"
- "Domain not resolving after NS change"

A bare health check ID + any symptom ("health check broken", "failover
not working") also routes here via the orchestrator.

## Inputs

- Symptom description: health check status (healthy/unhealthy/flapping),
  observed DNS response (old record, wrong record, no record),
  failover behaviour (not triggering, slow, wrong endpoint).
- Health check configuration: HealthCheckId, Type (HTTP/HTTPS/TCP/
  CALCULATED/CLOUDWATCH_METRIC), FQDN, IPAddress, Port, ResourcePath,
  RequestInterval, FailureThreshold, EnableSNI, ChildHealthChecks,
  Inverted, AlarmIdentifier.
- DNS/routing context: hosted zone ID, record set name and type,
  routing policy (FAILOVER/WEIGHTED/LATENCY/GEOLOCATION), TTL,
  HealthCheckId association on each record, NS delegation status.
- For live-account diagnosis: `get-health-check`,
  `get-health-check-status`, `list-resource-record-sets`,
  `describe-alarms`, `get-metric-statistics`, `dig`.

## Outputs

- One diagnostic block per target health check / domain / record set.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: certificate SAN update, health check config
  update, calculated HC logic fix, routing policy association, TTL
  adjustment, NS delegation fix, or INSUFFICIENT_DATA with missing
  fields listed.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Route 53 health check and
  DNS failover failures).
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when the
  health checker IPs cannot reach the endpoint due to VPC routing,
  SG, or peering issues.
- `/aws:audit-lambda-function` for checking if the endpoint Lambda
  behind the health check is itself failing.
