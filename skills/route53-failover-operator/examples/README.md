# End-to-end usage scenario: route53-failover-operator

A walkthrough showing the skill planning a planned weighted failover
operation on `api.example.com`, with all pre-checks passing and the
operator confirming at the CONFIRM gate. Contrasted with the BLOCKED
case where both primary and secondary health checks are unhealthy.

## Input (user prompt)

> We have `api.example.com` in hosted zone `Z2ABCDEFGHIJK` with
> weighted routing. Blue (10.0.0.10) is currently weight 100; green
> (10.0.1.10) is weight 0. We want to shift traffic to green as a
> planned failover. Both health checks are Healthy. TTL is 60s.

```json
{
  "Operation": "planned-failover",
  "FQDN": "api.example.com",
  "HostedZoneId": "Z2ABCDEFGHIJK",
  "RoutingPolicy": "weighted",
  "CurrentState": {
    "blue": {"Weight": 100, "IP": "10.0.0.10", "HealthCheckId": "h-blue123", "Status": "Healthy"},
    "green": {"Weight": 0, "IP": "10.0.1.10", "HealthCheckId": "h-abcdef1234", "Status": "Healthy"}
  },
  "TTL": 60,
  "TargetState": {"blue": {"Weight": 0}, "green": {"Weight": 100}}
}
```

## Skill output

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
  - [PASS] Green endpoint 10.0.1.10 reachable on port 443
  - [PASS] Green health check h-abcdef1234 Status: Healthy
  - [PASS] Current TTL: 60s (acceptable for fast failover)
  - [PASS] CloudWatch alarm api-example-failover exists
STEPS:
  1. CONFIRM: About to flip weighted routing on api.example.com in
     hosted zone Z2ABCDEFGHIJK. Blue 100->0; Green 0->100. Traffic
     shifts from 10.0.0.10 to 10.0.1.10. Propagation bounded by 60s
     TTL. Proceed? (yes/no)
  2. aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
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
  3. Poll: aws route53 get-change --id <change-id> until INSYNC.
POST_VERIFY:
  - (pending execution)
NOTES:
  - DNS propagation: up to 60s for cached resolvers. Rollback: re-run
    the change-batch with weights inverted (blue=100, green=0).
```

## Contrast — BLOCKED case (both records unhealthy)

If the secondary endpoint were also unreachable, the pre-check gate
would fire and no CLI would execute:

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
  - [INFO] test-dns-answer returns BOTH IPs — Route 53 in last-resort
STEPS: (none — secondary is also down)
POST_VERIFY: (none)
NOTES:
  - Root cause: failover target (secondary) also unreachable. Route 53
    returns both records (last-resort behavior).
  - Fix order: restore the secondary first; verify h-secondary flips
    to Healthy; then diagnose the primary separately.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the change-batch directly. The skill runs pre-checks (health
   checks healthy, TTL appropriate, secondary reachable) and BLOCKS
   before flipping traffic to a target that may be down.

2. **Both-records-unhealthy detection.** A generic assistant flips the
   weights regardless. The skill detects that BOTH records are
   unhealthy and BLOCKS — Route 53 is in last-resort mode, so
   changing weights does not help.

3. **TTL-aware propagation estimate.** A generic assistant says
   "failover is instant." The skill names the TTL-bounded propagation
   window (60s for cached resolvers, near-instant for uncached).

4. **Atomic change-batch for the pair.** A generic assistant might
   submit two separate change-batches (one per record). The skill
   upserts BOTH records in a single change-batch to avoid an
   inconsistent intermediate state.

5. **Rollback command ready.** A generic assistant omits rollback.
   The skill keeps the rollback change-batch (inverted weights) ready.

6. **`test-dns-answer` for authoritative verification.** A generic
   assistant verifies with `dig` only (which is subject to recursive
   resolver caching). The skill uses `test-dns-answer` for
   authoritative truth AND `dig` from multiple resolvers for observed
   truth.

7. **Calculated health check recommendation.** A generic assistant
   omits the false-healthy trap. The skill recommends pairing the
   endpoint health check with a CloudWatch-alarm-based calculated
   check so that a shallow `/health` probe does not mask a real
   outage.

## Slash-command invocation

```
/aws:operate-route53-failover
```

Or via the orchestrator:

```
/aws:pipeline
You: "failover api.example.com to green"
```

The orchestrator emits
`[Phase: Operate | Skills routed: route53-failover-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "failover api.example.com to green"
# [Phase: Operate | Skills routed: route53-failover-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the failover completes:

```bash
# Verify Route 53's authoritative answer
aws route53 test-dns-answer \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --record-name api.example.com \
  --record-type A \
  --resolver-ip 1.1.1.1 \
  --profile default

# Verify observed answer from major resolvers
dig @1.1.1.1 api.example.com +short
dig @8.8.8.8 api.example.com +short

# Confirm health check status
aws route53 get-health-check-status \
  --health-check-id h-abcdef1234 \
  --profile default

# Watch the application error-rate dashboard for 2x TTL post-change
aws cloudwatch get-metric-statistics \
  --namespace AppMetrics \
  --metric-name ErrorRate \
  --dimensions Name=Service,Value=api \
  --start-time $(date -u -v-2m +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average \
  --profile default
```
