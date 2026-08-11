# Cutover and Rollback Procedures Reference

Load this reference when executing a DNS cutover or rollback for a
CLB-to-ALB migration. Covers weighted routing phases, direct swap,
validation gates, and rollback steps.

## Weighted routing cutover (recommended for high-traffic)

Route 53 weighted routing shifts traffic incrementally from CLB to ALB.
Both load balancers stay provisioned; only the weights change.

### Prerequisites

- Both CLB and ALB are provisioned and serving 200s.
- Route 53 hosted zone has the application DNS name (e.g.,
  `app.example.com`) as an A record aliasing the CLB.
- The ALB DNS name is known (`dualstack.prod-alb-...elb.amazonaws.com`).
- CloudWatch dashboards for both CLB (`AWS/ELB` namespace) and ALB
  (`AWS/ApplicationELB` namespace) are ready.
- Baseline metrics captured: RequestCount, 5xx rate, p99 latency over
  the last 24 hours.

### Phase sequence

| Phase | CLB weight | ALB weight | Hold time | Gate to advance |
|---|---|---|---|---|
| 1 (canary) | 95 | 5 | 1 hour | ALB 5xx rate <= CLB baseline + 10%; p99 latency <= baseline + 20ms |
| 2 | 75 | 25 | 1 hour | Same gate |
| 3 | 50 | 50 | 2 hours | Same gate |
| 4 | 25 | 75 | 1 hour | Same gate |
| 5 (complete) | 0 | 100 | permanent | Final validation |

### Route 53 change command (Phase 1)

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Comment": "CLB-to-ALB migration Phase 1: 5% to ALB",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.example.com.",
        "Type": "A",
        "SetIdentifier": "clb",
        "Weight": 95,
        "AliasTarget": {
          "HostedZoneId": "Z3DZXE0K...",
          "DNSName": "dualstack.prod-clb-123.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.example.com.",
        "Type": "A",
        "SetIdentifier": "alb",
        "Weight": 5,
        "AliasTarget": {
          "HostedZoneId": "Z1P...",
          "DNSName": "dualstack.prod-alb-456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}'
```

### Validation gates (run at each phase)

1. `aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
   --metric-name HTTPCode_Target_5XX_Count --dimensions
   Name=LoadBalancer,Value=<alb-suffix> ...` — 5xx rate within baseline.
2. `aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB
   --metric-name TargetResponseTime ...` — p99 within baseline + 20ms.
3. `aws elbv2 describe-target-health --target-group-arn <tg-arn>` — all
   targets healthy (no targets drained by the incremental shift).
4. Application canary / synthetic check passes on the ALB's direct DNS
   name.
5. No client-reported errors in the canary dashboard.

If ANY gate fails, run rollback immediately.

## Direct swap cutover (low-traffic / internal services)

For internal services or low-traffic workloads where a 60s TTL blip is
acceptable, a direct alias swap is simpler than weighted routing.

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Comment": "CLB-to-ALB direct swap",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "internal.example.com.",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z1P...",
          "DNSName": "dualstack.prod-alb-456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}'
```

The CLB stays provisioned (for rollback). DNS propagates within 60s
(ALB DNS TTL).

## Rollback procedure

Rollback is a weight flip. Takes effect within the DNS TTL (60s).

### Weighted rollback

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Comment": "Rollback: 100% to CLB",
  "Changes": [
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":100,"AliasTarget":{"HostedZoneId":"Z3DZXE0K...","DNSName":"dualstack.prod-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}},
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"alb","Weight":0,"AliasTarget":{"HostedZoneId":"Z1P...","DNSName":"dualstack.prod-alb-456.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}}
  ]
}'
```

### Direct-swap rollback

```bash
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Comment": "Rollback direct swap: back to CLB",
  "Changes": [
    {"Action":"UPSERT","ResourceRecordSet":{"Name":"internal.example.com.","Type":"A","AliasTarget":{"HostedZoneId":"Z3DZXE0K...","DNSName":"dualstack.prod-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}}
  ]
}'
```

### Post-rollback verification

- CLB RequestCount returns to baseline (CloudWatch `AWS/ELB`).
- ALB RequestCount drops to near-zero (residual from cached DNS).
- Application error rate returns to baseline.
- Document the rollback reason and timing for the post-mortem.

## CLB cleanup (post-migration, after observation window)

Only after the observation window (24-72 hours) with no rollback:

```bash
# 1. Remove the CLB weighted record (keep the ALB record)
aws route53 change-resource-record-sets --hosted-zone-id Z111 --change-batch '{
  "Changes": [
    {"Action":"DELETE","ResourceRecordSet":{"Name":"app.example.com.","Type":"A","SetIdentifier":"clb","Weight":0,"AliasTarget":{"HostedZoneId":"Z3DZXE0K...","DNSName":"dualstack.prod-clb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}}}
  ]
}'

# 2. Delete the CLB
aws elb delete-load-balancer --load-balancer-name prod-clb

# 3. (Optional) Delete the CLB's security group if no other resource uses it
aws ec2 delete-security-group --group-id sg-clb-old
```

Do NOT delete the CLB during the observation window — it is the rollback
target.

## Common cutover pitfalls

- **TTL + client-side caching.** The ALB/CLB DNS TTL is 60s, but
  application-level connection pools and HTTP keep-alive can hold
  connections to the CLB for minutes. Weighted routing handles this
  gracefully; direct swap may see residual CLB traffic for 5-10 minutes.
- **Route 53 change propagation.** Route 53 applies the change within
  ~60s, but global resolver propagation can take longer. Use
  `EvaluateTargetHealth: true` so Route 53 stops routing to an unhealthy
  LB automatically.
- **Connection draining at 100% shift.** When the CLB weight goes to 0,
  in-flight connections drain over `ConnectionDraining.timeout`. New
  connections go to the ALB. Monitor the CLB's `HealthyHostCount` and
  `RequestCount` — they should drop to zero over the drain window.
- **SSL certificate renewal during migration.** If the ACM cert is
  pending renewal during the cutover window, renewal may fail because
  the validation record still points to the CLB. Complete the cutover
  before the renewal window, or validate via DNS.
