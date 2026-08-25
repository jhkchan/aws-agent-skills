# Worked Examples — Route 53 Health Check Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Worked example — Failure threshold math (failover delay)

```text
TARGET: health-check hc-xyz789 / weighted routing
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Health check RequestInterval is 30s and FailureThreshold is 3.
  Failover takes 90 seconds (3 x 30s) after the endpoint stops
  responding. Combined with the record TTL of 300s, total failover
  time can be up to 390 seconds (6.5 minutes). The operator expected
  sub-minute failover (Step 5 / Step 0).
LAYER: HC_INTERVAL_THRESHOLD
EVIDENCE:
  - Symptom: after the primary endpoint went down at T+0, DNS did not
    switch to the secondary until T+7 minutes.
  - Probe: aws route53 get-health-check returns RequestInterval: 30,
    FailureThreshold: 3. Total detection time = 90 seconds.
  - Probe: dig +short api.example.com returns TTL 300 on the weighted
    record. Total failover = 90s + 300s = 390s max.
  - Passing: health check is correctly associated with the primary
    record (not a routing policy issue); SG allows health checker IPs
    (not a network issue).
REMEDIATION:
  1. Lower FailureThreshold to 1 for faster detection:
     aws route53 update-health-check --health-check-id hc-xyz789 \
       --failure-threshold 1
  2. Switch to fast health checks (10s interval) for faster detection:
     aws route53 update-health-check --health-check-id hc-xyz789 \
       --request-interval 10  (note: fast health checks incur higher
       cost)
  3. Lower the record TTL to 60 seconds for faster client failover:
     aws route53 change-resource-record-sets --hosted-zone-id Z123 \
       --change-batch '{"Changes":[{"Action":"UPSERT",...,"TTL":60}]}'
  4. Verify: stop the endpoint and time how long until dig returns the
     secondary IP (target: < 70 seconds with threshold 1, interval 10,
     TTL 60).
CONFIRM: Before changing the health check and TTL, emit: "CONFIRM:
  About to lower FailureThreshold to 1, switch to 10s interval, and
  set TTL to 60 on api.example.com. Proceed? (yes/no)"
```

## Worked example — INSUFFICIENT_DATA

```text
TARGET: health-check unknown / example.com
VERDICT: INSUFFICIENT_DATA
REASON: Symptom is "DNS failover is not working for example.com" but
  the health check ID, routing policy type, record TTL, and NS
  delegation status are not provided. Without these, it is impossible
  to distinguish a health check config issue, a routing policy
  association issue, a DNS TTL caching issue, or an NS delegation
  problem.
LAYER: UNKNOWN
EVIDENCE:
  - Symptom: failover is not triggering for example.com.
  - Missing: HealthCheckId, routing policy (FAILOVER / WEIGHTED /
    LATENCY / GEOLOCATION), record TTL, hosted zone ID, NS delegation
    status.
  - Missing: get-health-check-status output showing healthy/unhealthy.
REMEDIATION: Provide: (1) the HealthCheckId and get-health-check-status
  output, (2) the hosted zone ID and list-resource-record-sets for the
  domain, (3) the routing policy and TTL on the primary and secondary
  records, (4) dig NS example.com output, and (5) whether the health
  check reports unhealthy after the endpoint is confirmed down.
```
