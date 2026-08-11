# End-to-end usage scenario: elb-cost-optimizer

A walkthrough showing the skill optimizing a high-LCU ALB with disabled
keep-alive. This exercises Step 3 (LCU_DIM), Step 4 (CONSOLIDATION),
and the estimated savings calculation.

## Input (user prompt)

> My ALB `web-frontend-prod` serves a high-traffic web app.
> ConsumedLCUs average 18.0, max 25.0. The peak dimension is new
> connections at 500/sec (20 LCU). HTTP keep-alive is disabled on the
> nginx targets. Cost Explorer shows $121.54/month in LCU charges +
> $16.43/month base = $137.97/month total. The app serves short-lived
> REST API requests from mobile clients.

## Skill output

```text
TARGET: web-frontend-prod (ALB, us-east-1, vpc-prod)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Peak LCU dimension is new connections at 20.0 LCU (500/sec).
Active connections is 4.0 LCU, processed bytes is 1.5 LCU, rule
evaluations is 2.0 LCU. The peak dimension dominates (20/27.5 = 73%
of theoretical sum). Root cause: HTTP keep-alive disabled on nginx
targets — every request opens a new TCP+TLS connection, inflating the
new connection rate.
RECOMMENDATION:
  1. LCU_DIM: Enable HTTP keep-alive on nginx targets. This reduces
     new connection rate by 80%+ (from 500/sec to ~100/sec), dropping
     the peak LCU from 20.0 to ~4.0.
  2. LCU_DIM: Reduce ALB idle timeout from 60s (default) to 30s to
     lower active connection count (secondary benefit).
ESTIMATED_SAVINGS: ~$84.06/month ($1,008.72/year)
  - Current LCU cost: 18.0 avg LCU x $0.008 x 730 = $105.12/month
  - Post-keep-alive LCU cost: 4.0 avg LCU x $0.008 x 730 = $23.36/month
  - LCU savings: $81.76/month
  - Idle timeout reduction: ~$2.30/month additional from active
    connection LCU drop
  - Total monthly savings: ~$84.06
ACTION_STEPS:
  1. Enable keep-alive in nginx config:
     Add `keepalive_timeout 65;` and `keepalive_requests 100;` to
     nginx.conf. Remove any `Connection: close` headers in the
     application response.
  2. Reduce ALB idle timeout:
     aws elbv2 modify-load-balancer-attributes \
       --load-balancer-arn <lb-arn> \
       --attributes Key=idle_timeout.timeout_seconds,Value=30
  3. Monitor ConsumedLCUs for 7 days post-change:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/ApplicationELB \
       --metric-name ConsumedLCUs \
       --dimensions Name=LoadBalancer,Value=app/web-frontend-prod/... \
       --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
       --period 3600 --statistics Average Maximum
  4. If LCU drops below 5.0, the optimization is confirmed. If not,
     investigate whether mobile clients are reusing connections.
```

## What the skill caught that a generic assistant misses

1. **The max-not-sum LCU billing model.** A generic assistant might
   recommend reducing "all dimensions" equally. The skill identifies
   that new connections (20 LCU) is the peak and the other three
   dimensions (totaling 7.5 LCU) are irrelevant — reducing them saves
   nothing because the bill is based on the max.

2. **The keep-alive leverage.** A generic assistant says "enable
   keep-alive" but does not quantify the LCU impact. The skill
   calculates that keep-alive reduces new connections from 500/sec
   to ~100/sec (mobile clients reuse connections for multiple API
   calls within a session), dropping the peak from 20 LCU to 4 LCU —
   a 76% LCU reduction.

3. **The idle timeout secondary benefit.** A generic assistant does
   not connect the ALB idle timeout to the active connections LCU
   dimension. The skill identifies that reducing the timeout from 60s
   to 30s halves the average active connection duration, providing a
   secondary savings of ~$2.30/month.

4. **The monitoring plan.** A generic assistant does not provide
   post-change verification commands. The skill provides the exact
   CloudWatch command to verify the LCU drop over 7 days, with a
   success criterion (LCU < 5.0).

## Slash-command invocation

```
/aws:optimize-elb-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "web-frontend-prod ALB at 18 avg LCU, $138/month — optimise"
```

The orchestrator emits `[Phase: Optimize | Skills routed:
elb-cost-optimizer]` and hands off to this skill for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has AWS credentials:

```bash
# Read the ALB configuration and LCU metrics.
aws elbv2 describe-load-balancers \
  --names web-frontend-prod \
  --query 'LoadBalancers[*].{arn:LoadBalancerArn,type:Type,dns:DNSName,scheme:Scheme}'

aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value=app/web-frontend-prod/1234567890/... \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Pull per-dimension metrics to identify the peak.
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name NewConnectionCount \
  --dimensions Name=LoadBalancer,Value=app/web-frontend-prod/1234567890/... \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Modify the ALB idle timeout.
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <lb-arn> \
  --attributes Key=idle_timeout.timeout_seconds,Value=30
```

The 500/sec new connection rate with keep-alive disabled is the
classic mobile API pattern — each API call opens a new connection.
Enabling keep-alive allows the mobile client's HTTP library to reuse
the TCP+TLS connection for subsequent requests, reducing the new
connection rate by 80%+.
