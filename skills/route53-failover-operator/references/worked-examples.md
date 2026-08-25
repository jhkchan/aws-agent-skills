# Worked Examples — Route 53 Failover Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Canonical output template

```text
OPERATION: <planned-failover | emergency-failover | failback | create-health-check | update-health-check | diagnose-failover | update-routing>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <fqdn> (hosted zone: <id>, routing policy: <policy>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command or change-batch JSON with all fields populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <TTL, propagation estimate, monitoring, caveats>
```

## Worked example — planned-failover (weighted 100/0 -> 0/100)

```text
OPERATION: planned-failover
VERDICT: READY
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        weighted)
PRE_CHECKS:
  - [PASS] Hosted zone Z2ABCDEFGHIJK exists, not deleted
  - [PASS] Weighted records found:
    api.example.com A SetIdentifier=blue  Weight=100  Value=10.0.0.10
    api.example.com A SetIdentifier=green Weight=0    Value=10.0.1.10
  - [PASS] Green endpoint 10.0.1.10 reachable on port 443 (TCP probe OK)
  - [PASS] Green health check h-abcdef1234 Status: Healthy
  - [PASS] Current TTL: 60s (acceptable for fast failover)
  - [PASS] Cross-account IAM: operator role authorized in zone account
  - [PASS] CloudWatch alarm api-example-failover exists on
    AWS/Route53 HealthCheckStatus
STEPS:
  1. CONFIRM: About to flip weighted routing on api.example.com in
     hosted zone Z2ABCDEFGHIJK (account 111111111111, global Route 53).
     Blue weight 100->0; Green weight 0->100. Traffic will shift from
     10.0.0.10 (blue) to 10.0.1.10 (green). DNS propagation bounded by
     60s TTL. Proceed? (yes/no)
  2. aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.",","Type":"A",
             "SetIdentifier":"blue","Weight":0,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
             "HealthCheckId":"h-blue123"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"green","Weight":100,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
             "HealthCheckId":"h-abcdef1234"}}
         ]
       }'
  3. Capture ChangeInfo.Id; poll:
     aws route53 get-change --id <change-id>
     until Status: INSYNC (typically 5-30 seconds).
POST_VERIFY:
  - (pending execution)
NOTES:
  - DNS propagation: up to 60s for cached recursive resolvers (TTL).
    Uncached resolvers see the new answer within seconds of INSYNC.
  - Rollback: re-run the same change-batch with weights inverted
    (blue=100, green=0). Keep the rollback command ready.
  - Watch the application error-rate dashboard for 2x TTL post-change
    (120s) to catch a bad green deployment before declaring COMPLETED.
```

## Emergency failover worked example (TTL lowering required)

### Worked example — emergency-failover (TTL lowering required)

```text
OPERATION: emergency-failover
VERDICT: READY
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        failover)
PRE_CHECKS:
  - [PASS] Failover records found:
    api.example.com A SetIdentifier=primary   Failover=PRIMARY
      Value=10.0.0.10 HealthCheckId=h-primary
    api.example.com A SetIdentifier=secondary Failover=SECONDARY
      Value=10.0.1.10
  - [PASS] PRIMARY health check h-primary Status: Unhealthy
    (reason: Connection timed out, 3 consecutive failures)
  - [PASS] Secondary endpoint 10.0.1.10 reachable on port 443
  - [PASS] CloudWatch alarm api-example-failover in ALARM state
  - [WARN] Current TTL: 300s — lowering to 60s FIRST to shrink the
    stale-traffic window. The full failover will take up to old-TTL
    (300s) for clients that cached at 300s; new clients see 60s.
STEPS:
  1. CONFIRM: About to lower TTL on api.example.com failover records
     from 300s to 60s in hosted zone Z2ABCDEFGHIJK. Then, after old TTL
     expires, swap PRIMARY and SECONDARY values (10.0.0.10 becomes
     SECONDARY, 10.0.1.10 becomes PRIMARY). This redirects traffic from
     the down primary to the secondary. Proceed? (yes/no)
  2. Phase 1 — lower TTL (apply immediately, then wait old-TTL seconds):
     aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"primary","Failover":"PRIMARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
             "HealthCheckId":"h-primary"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"secondary","Failover":"SECONDARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}]}}
         ]
       }'
     # Wait 300 seconds (old TTL) for resolver caches to expire.
  3. Phase 2 — swap topology after old TTL expires:
     aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"primary","Failover":"PRIMARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
             "HealthCheckId":"h-secondary"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"secondary","Failover":"SECONDARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}]}}
         ]
       }'
  4. Poll: aws route53 get-change --id <change-id> until INSYNC.
POST_VERIFY:
  - (pending execution)
NOTES:
  - Emergency mode: the primary is already unhealthy. Route 53 SHOULD
    already be serving the secondary (10.0.1.10) for clients whose
    caches expired. Verify with test-dns-answer and dig BEFORE running
    Phase 2 — if Route 53 is already serving 10.0.1.10, you only need
    Phase 1 (TTL lowering) and can defer Phase 2 (topology swap) until
    the primary is restored.
  - Bring a new health check online for the new primary (10.0.1.10)
    before the swap, OR confirm the existing h-secondary health check
    is wired to 10.0.1.10 and reports Healthy.
```

## Diagnose-failover worked example (BLOCKED with remediation)

### Worked example — diagnose-failover (BLOCKED with remediation)

```text
OPERATION: diagnose-failover
VERDICT: BLOCKED
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        failover)
PRE_CHECKS:
  - [PASS] Hosted zone exists, failover records present
  - [PASS] PRIMARY health check h-primary Status: Unhealthy
  - [FAIL] SECONDARY health check h-secondary Status: Unhealthy
    (reason: "Connection timed out" from all 3 checker regions)
  - [INFO] test-dns-answer returns BOTH IPs (10.0.0.10 and 10.0.1.10) —
    Route 53 is in last-resort mode because both records are unhealthy
STEPS: (none — secondary is also down)
POST_VERIFY: (none)
NOTES:
  - Root cause: the failover target (secondary) is also unreachable.
    Route 53 returns both records because it prefers a possibly-bad
    answer over no answer.
  - Fix order:
    1. Restore the secondary endpoint 10.0.1.10 (restart service /
       fix network / fail over the underlying compute).
    2. Verify h-secondary flips to Healthy:
       aws route53 get-health-check-status --health-check-id h-secondary
    3. Once secondary is Healthy, test-dns-answer should return only
       10.0.1.10. Confirm before any further routing changes.
    4. Then diagnose and restore the primary separately; failback only
       when h-primary has been Healthy for >= 2 consecutive intervals.
```
