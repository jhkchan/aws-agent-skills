# clb-to-alb-migration-operator — worked examples (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Worked example — cutover-dns (Phase 1, 5% weighted, READY)

```text
OPERATION: cutover-dns
VERDICT: READY
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] ALB exists, State: active
  - [PASS] All targets healthy in tg-web-8080 (3/3 healthy)
  - [PASS] ALB responds 200 on https://prod-web-alb-.../healthz from
    a canary client
  - [PASS] Route 53 hosted zone Z111 has app.example.com A record
    aliasing CLB (weight 100 implied)
  - [PASS] CloudWatch baseline: RequestCount ~5000/min, 5xx ~0
STEPS:
  1. CONFIRM: About to shift app.example.com to 95% CLB / 5% ALB via
     Route 53 weighted routing. This routes ~250 req/min to the ALB.
     Proceed? (yes/no)
  2. aws route53 change-resource-record-sets --hosted-zone-id Z111
     --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":
     {"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":95,
     "AliasTarget":{"HostedZoneId":"Z3DZXE0K...","DNSName":"dualstack.prod-
     web-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}},
     {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.",
     "Type":"A","SetIdentifier":"alb","Weight":5,"AliasTarget":{...}}]}'
  3. Monitor 15 minutes: CloudWatch HTTPCode_Target_5XX_Count on ALB;
     if > baseline+10%, run rollback (Step 5 of Process).
POST_VERIFY:
  - (pending execution)
NOTES:
  - TTL 60s — clients pick up the new weight within ~60s.
  - Next phase (25% ALB) after 1 hour at 5% with no regression.
  - Rollback: UPSERT weights to 100/0 (CLB/ALB). Takes effect in 60s.
```

## Worked example — cutover-dns (BLOCKED, Proxy Protocol backend)

```text
OPERATION: cutover-dns
VERDICT: BLOCKED
TARGET: prod-game-clb -> prod-game-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] ALB exists, State: active
  - [FAIL] CLB Policy ProxyProtocolPolicyType enabled on backend port
    4242 — the Go backend parses Proxy Protocol v2 frames. ALB does NOT
    emit Proxy Protocol; the backend will receive HTTP bytes and try to
    parse them as a Proxy Protocol header, producing 400/connection
    reset for 100% of requests.
STEPS: (none — backend incompatible)
POST_VERIFY: (none)
NOTES:
  - Root cause: ALB cannot emit Proxy Protocol. The backend must be
    reconfigured to read X-Forwarded-For / X-Forwarded-Proto headers
    instead of Proxy Protocol frames.
  - Fix: (a) update the backend listener to disable Proxy Protocol
    parsing and read X-Forwarded-For, OR (b) keep this listener on an
    NLB (which supports Proxy Protocol v2) and migrate only HTTP/HTTPS
    listeners to ALB.
```

## Worked example — verify-cutover (COMPLETED)

```text
OPERATION: verify-cutover
VERDICT: COMPLETED
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Route 53 weights: ALB 100, CLB 0
  - [PASS] DNS globally resolves to ALB (TTL elapsed 24h ago)
STEPS:
  1. aws elbv2 describe-target-health --target-group-arn <tg-web-8080>
  2. aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
     --metric-name HTTPCode_Target_5XX_Count ...
  3. aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
     --metric-name TargetResponseTime ...
POST_VERIFY:
  - [PASS] describe-target-health: 3/3 targets State: healthy
  - [PASS] HTTPCode_Target_5XX_Count: 0 over last 60 minutes (CLB
    baseline was 0-2/min)
  - [PASS] TargetResponseTime p99: 85ms (CLB baseline was 90ms)
  - [PASS] ALB access logs in S3 show target_status_code 2xx for 100%
    of /api/* requests
  - [PASS] No client-reported errors in the canary dashboard
NOTES:
  - Cutover complete. Schedule CLB deletion after 72-hour observation
    window (2026-08-12).
  - Keep Route 53 weighted record at ALB:100, CLB:0 until CLB deletion,
    then remove the CLB weighted record.
  - Post-migration optimization: consider adding ALB WAF for SQLi/XSS
    protection (was not possible on CLB).
```
