# Route 53 Pricing and Configuration Reference

Supplementary reference for the Route 53 Cost Optimizer skill. Loaded
on-demand when detailed pricing math, health check configuration, routing
policy surcharge details, or DNSSEC setup steps are needed.

## Route 53 pricing (us-east-1, 2026, USD)

### Hosted zone pricing

| Zone tier | Monthly cost per zone | Notes |
|---|---|---|
| First 25 hosted zones | $0.50/zone/month | Public and private zones billed the same |
| 26+ hosted zones | $0.10/zone/month | Volume discount tier |

### Standard DNS query pricing

| Query volume tier | $/billion queries | Notes |
|---|---|---|
| First 1 billion/month | $0.40/B | Standard queries (simple, weighted, failover, geoproximity) |
| Over 1 billion/month | $0.20/B | Volume discount tier |

### Routing policy surcharges (per billion queries, ON TOP of base)

| Policy type | Surcharge | Total $/B (first tier) | Notes |
|---|---|---|---|
| Simple / Weighted / Failover | $0.00 | $0.40/B | No surcharge |
| Latency-based routing | +$0.20/B | $0.60/B | Charges on top of standard rate |
| Geolocation routing | +$0.30/B | $0.70/B | Charges on top of standard rate |
| Geoproximity routing | +$0.30/B | $0.70/B | Traffic policy required |

### Health check pricing

| Check type | Monthly cost | Notes |
|---|---|---|
| Endpoint health check | $0.50/month | First 50 checks; $0.10/month for 51+ |
| Calculated health check | $0.00/month (FREE) | Monitors up to 25 other checks |
| Alarm-based health check | $0.50/month | Monitors a CloudWatch alarm state |

### Traffic policy pricing

| Component | Cost | Notes |
|---|---|---|
| Per traffic policy | $50.00/month flat | Billed once per policy, not per record |
| Per million policy queries | $0.50/M queries | First 1B queries included in some tiers |

### DNSSEC pricing

| Component | Cost | Notes |
|---|---|---|
| Route 53 DNSSEC signing | $0.00/month | Signing is free |
| KMS key (signing) | $1.00/month | Customer-managed KMS key for key-signing-key |
| KMS API calls (signing) | $0.03/10K calls | One signature per zone update |

### Domain registration (separate from hosted zone billing)

Domain registration and transfer are billed separately from hosted zones
and are NOT affected by zone deletion or consolidation. This skill does
not optimize domain registration costs.

## Hosted zone limits

| Limit | Value | Notes |
|---|---|---|
| Zones per account | 500 (soft) | Increase via support case |
| Records per zone | 10,000 (soft) | Increase via support case |
| Health checks per account | 200 (soft) | Calculated checks do not count toward limit |
| Calculated health check children | 25 per calculated check | One level of nesting only |
| Traffic policies per account | 50 (soft) | Increase via support case |

## Health check configuration details

### Endpoint health check lifecycle

```
Create:    aws route53 create-health-check --caller-reference <ref>
           --health-check-config Type=HTTP,IPAddress=<ip>,Port=80
           Cost: $0.50/month begins immediately
Delete:    aws route53 delete-health-check --health-check-id <id>
           Cost stops at end of current billing period
```

### Calculated health check setup

A calculated health check monitors the status of up to 25 other health
checks. It is FREE ($0/month).

```bash
aws route53 create-health-check \
  --caller-reference calc-check-$(date +%s) \
  --health-check-config '
    {
      "Type": "CALCULATED",
      "HealthThreshold": 2,
      "ChildHealthChecks": [
        "<check-id-1>",
        "<check-id-2>",
        "<check-id-3>"
      ]
    }
  '
```

**Nesting limit:** Calculated health checks cannot monitor other
calculated health checks. Only one level of nesting is supported. The
maximum fan-in is 25 endpoint checks per calculated check.

### Health check interval and cost

The health check interval (10s, 30s) does NOT affect cost. All endpoint
checks are $0.50/month regardless of interval. Interval is a reliability
decision, not a cost decision.

## Routing policy CLI reference

### Change routing policy from latency to weighted

```bash
# Delete the latency-based record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z-xxx \
  --change-batch '
    {
      "Changes": [
        {
          "Action": "DELETE",
          "ResourceRecordSet": {
            "Name": "app.example.com.",
            "Type": "A",
            "SetIdentifier": "us-east-primary",
            "Region": "us-east-1",
            "AliasTarget": {
              "HostedZoneId": "Z2FDTNDATAQYW2",
              "DNSName": "alb-xxx.us-east-1.elb.amazonaws.com",
              "EvaluateTargetHealth": true
            }
          }
        }
      ]
    }'

# Create weighted records instead
aws route53 change-resource-record-sets \
  --hosted-zone-id Z-xxx \
  --change-batch '
    {
      "Changes": [
        {
          "Action": "CREATE",
          "ResourceRecordSet": {
            "Name": "app.example.com.",
            "Type": "A",
            "SetIdentifier": "primary",
            "Weight": 100,
            "AliasTarget": {
              "HostedZoneId": "Z2FDTNDATAQYW2",
              "DNSName": "alb-xxx.us-east-1.elb.amazonaws.com",
              "EvaluateTargetHealth": true
            }
          }
        }
      ]
    }'
```

## DNSSEC configuration reference

### Enable DNSSEC on a hosted zone

```bash
# 1. Create a KMS key for signing
aws kms create-key --key-spec RSA_2048 --origin AWS_KMS \
  --description "Route53 DNSSEC signing for example.com"

# 2. Enable DNSSEC on the zone
aws route53 enable-hosted-zone-dnssec --hosted-zone-id Z-xxx

# 3. Create a key-signing-key (KSK)
aws route53 create-key-signing-key \
  --hosted-zone-id Z-xxx \
  --key-management-service-arn arn:aws:kms:... \
  --name example-ksk \
  --status ACTIVE

# 4. Establish chain of trust (DS record at parent zone/registrar)
```

### Disable DNSSEC

```bash
aws route53 delete-key-signing-key --hosted-zone-id Z-xxx --key-id <ksk-id>
# Then remove the DS record at the parent/registrar
# KMS key can then be deleted separately
```

## Query logging configuration

### Enable query logging

```bash
aws route53 create-query-logging-config \
  --hosted-zone-id Z-xxx \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:...:log-group:/aws/route53/example.com
```

### Estimate log volume

```
log_GB_per_month = (monthly_queries × 200) / (1024^3)

Example: 100M queries/month → ~18.6 GB → $9.28/month ingestion
         500M queries/month → ~93 GB → $46.56/month ingestion
```

## Extended anti-pattern catalog

1. **NEVER delete a hosted zone that hosts an ACM certificate validation
   CNAME.** The certificate will fail renewal within 60 days.

2. **NEVER assume a zone with zero queries is safe to delete.** Some
   zones exist solely for email (MX) or certificate validation (CNAME).
   Check record sets thoroughly.

3. **NEVER disable DNSSEC without removing the DS record at the parent
   zone or registrar first.** Stale DS records cause validation failures.

4. **NEVER delete a traffic policy while it is still attached to a
   record.** Remove all policy instances first.

5. **NEVER reduce health check interval as a cost-saving measure.** The
   cost is flat regardless of interval.

6. **NEVER recommend geolocation routing for a zone that serves a single
   country.** The surcharge is only justified for multi-region targeting.

7. **NEVER consolidate zones that serve different compliance domains**
   (e.g., PCI zone and public marketing zone).

## Regional pricing notes

Route 53 pricing is global — the same rates apply in all regions. There
is no regional multiplier for Route 53 hosted zones, health checks, or
queries. KMS key costs (for DNSSEC) follow regional KMS pricing.
