# Route 53 Health Check Procedures Reference

Load this reference when creating, updating, or diagnosing a Route 53
health check. The procedures below are the canonical sequences for each
health-check archetype, with the read-only diagnostic commands and the
CLI to fix each root cause.

## Decision tree — which health-check archetype

| Symptom | Use | Why |
|---|---|---|
| Endpoint HTTP/HTTPS probe | **Endpoint check** | Direct probe of IP/host:port/path; default 30s interval; configurable failure threshold |
| CloudWatch alarm in ALARM flips the check | **CloudWatch alarm check** | No per-endpoint fee; composite signal (error rate, latency) |
| Compose other checks with AND/OR | **Calculated check** | Up to 256 child checks; free parent; insulate children to prevent cross-contamination |
| Probe a TCP port (no HTTP) | **TCP check** | For databases, SSH, non-HTTP services |
| HTTP probe with string match | **Search-string check** | Verify the response body contains expected content |
| Multi-Region failover target | **Latency check + latency routing** | Route 53 measures latency per region automatically |

## Health check types

### Endpoint checks (HTTP, HTTPS, TCP)

The most common type. Route 53 checkers in 3+ global regions issue the
probe independently; a check is unhealthy only when the failure
threshold is met across the merged observations.

```bash
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "api.example.com",
    "IPAddress": "10.0.0.10",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "MeasureLatency": true,
    "EnableSNI": true
  }'
```

| Field | Effect |
|---|---|
| `Type` | `HTTP`, `HTTPS`, `HTTP_STR_MATCH`, `HTTPS_STR_MATCH`, `TCP`, `CALCULATED`, `CLOUDWATCH_METRIC` |
| `RequestInterval` | 10 (Fast) or 30 (Standard) seconds. 10s roughly doubles cost. |
| `FailureThreshold` | 1-10 consecutive failures before unhealthy. Default 3. |
| `EnableSNI` | Required for virtual-hosted TLS endpoints (multiple certs per IP). |
| `SearchString` | For `*_STR_MATCH` types. If the response body does not contain this string, the check is unhealthy. |
| `MeasureLatency` | Records latency per checker region in CloudWatch. Useful for latency-routing tuning. |
| `Regions` | Override the default checker regions. Defaults to 3 geographically diverse regions. |
| `Disabled` | Temporarily disable the check without deleting it. |

**Cost:** $0.50 per endpoint health check per month (first 100), then
$0.25 each. `RequestInterval: 10` does not double the fee (it is one
check), but increases probe volume. Calculated and CloudWatch-alarm
checks are free.

### CloudWatch-alarm-based checks

Drive the health check from a CloudWatch alarm in ALARM state. No per-
endpoint fee. Adds alarm-evaluation latency (typically 1 minute for a
1-minute period).

```bash
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "CLOUDWATCH_METRIC",
    "AlarmIdentifier": {
      "Region": "us-east-1",
      "Name": "api-error-rate-high"
    },
    "InsufficientDataHealthStatus": "LastKnownGoodStatus"
  }'
```

| `InsufficientDataHealthStatus` | Effect |
|---|---|
| `Healthy` | Treat insufficient data as healthy (optimistic). |
| `Unhealthy` | Treat insufficient data as unhealthy (fail-fast). |
| `LastKnownGoodStatus` | Preserve the previous status (smooth). Default. |

### Calculated health checks (AND/OR)

Compose other health checks. Parent is free; children are billed at
their own rates. Use to combine "endpoint responding" AND "no error-
rate alarm."

```bash
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "CALCULATED",
    "HealthThreshold": 2,
    "ChildHealthChecks": ["h-endpoint-1", "h-endpoint-2", "h-alarm-1"],
    "InsufficientDataHealthStatus": "Unhealthy"
  }'
```

`HealthThreshold` is the minimum number of child checks that must be
healthy for the parent to be healthy. For AND semantics, set it equal
to the number of children. For OR semantics, set it to 1.

### Insulated child checks

A child health check can be marked insulated so that its status does
not affect OTHER calculated checks that reference it. Use when sharing
a child check between calculated checks with different semantics.

```bash
aws route53 update-health-check \
  --health-check-id h-shared-1 \
  --reset-elements \
  --add-elements '{
    "Insulated": true
  }'
```

## Procedure: create a failover-ready health check

**Goal:** wire a health check to a failover routing record so that
Route 53 fails over when the primary is unhealthy.

```bash
# 1. Create the health check (HTTPS endpoint check)
HEALTH_CHECK_ID=$(aws route53 create-health-check \
  --caller-reference "failover-$(date +%s)" \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "api.example.com",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "EnableSNI": true,
    "MeasureLatency": true
  }' \
  --query 'HealthCheck.Id' --output text)

# 2. Wait for the first observation (typically 30-60 seconds)
aws route53 get-health-check-status --health-check-id $HEALTH_CHECK_ID

# 3. Wire the health check to the PRIMARY record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.example.com.",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "TTL": 60,
        "ResourceRecords": [{"Value": "10.0.0.10"}],
        "HealthCheckId": "'"$HEALTH_CHECK_ID"'"
      }
    }]
  }'

# 4. Verify the SECONDARY record exists (no health check needed)
aws route53 test-dns-answer \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --record-name api.example.com \
  --record-type A \
  --resolver-ip 1.1.1.1
```

## Procedure: diagnose a health check that won't go healthy

**Symptom:** `get-health-check-status` shows `Unhealthy` persistently.

```bash
# 1. Get the latest failure reason
aws route53 get-health-check-last-failure-reason \
  --health-check-id <id>

# 2. Per-region observations
aws route53 get-health-check-status --health-check-id <id>

# 3. Probe the endpoint directly from a third party (e.g., your laptop)
curl -v https://api.example.com/health
dig api.example.com +short

# 4. Verify Route 53 checker IPs can reach the endpoint
#    Route 53 checkers use a published prefix list — allow them on the
#    endpoint's security group / firewall.
aws ec2 describe-managed-prefix-lists \
  --query 'PrefixLists[?PrefixListName==`com.amazonaws.global.route53.healthcheck`].PrefixListId' \
  --output text
```

**Common findings and fixes:**

| Finding | Fix |
|---|---|
| "Connection timed out" from all checker regions | Endpoint firewall blocks Route 53 checker IPs. Allow the AWS Route 53 checker prefix list on the SG. |
| "No response from server" | Endpoint crashed or port closed. Restart the service. |
| "String not found in response body" | Application deployed a new build that changed `/health` response. Update `SearchString`. |
| 403 / 401 response | Endpoint requires auth. Use a dedicated unauthenticated `/health` route, or use a TCP check instead. |
| Self-signed cert error (HTTPS) | Route 53 does NOT validate the certificate by default for HTTPS (only HTTPS_STR_MATCH with EnableSNI). For strict validation, use a calculated check with an external monitor. |
| Healthy in some regions, unhealthy in others | Endpoint is geographically restricted. Configure the health check's `Regions` to match the endpoint's expected regions, or remove geo-restrictions on the endpoint. |

## Procedure: verify failover actually happened

After a health check flips unhealthy, Route 53 SHOULD stop returning
the PRIMARY record's IP. Verify end-to-end:

```bash
# 1. Authoritative truth: what does Route 53 say?
aws route53 test-dns-answer \
  --hosted-zone-id Z2ABCDEFGHIJK \
  --record-name api.example.com \
  --record-type A \
  --resolver-ip 1.1.1.1

# 2. Observed truth: what do major resolvers see?
dig @1.1.1.1 api.example.com +short
dig @8.8.8.8 api.example.com +short
dig @9.9.9.9 api.example.com +short

# 3. Health check status
aws route53 get-health-check-status --health-check-id <primary-hc>

# 4. CloudWatch metric for the health check
aws cloudwatch get-metric-statistics \
  --namespace AWS/Route53 \
  --metric-name HealthCheckPercentageHealthy \
  --dimensions Name=HealthCheckId,Value=<primary-hc> \
  --start-time $(date -u -v-15m +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average
```

If `test-dns-answer` returns the secondary IP but `dig` still returns
the primary, recursive resolvers are caching. Wait TTL seconds and
re-test.

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| List health checks | `aws route53 list-health-checks` |
| Health check config | `aws route53 get-health-check --health-check-id <id>` |
| Health check status | `aws route53 get-health-check-status --health-check-id <id>` |
| Last failure reason | `aws route53 get-health-check-last-failure-reason --health-check-id <id>` |
| Update health check | `aws route53 update-health-check --health-check-id <id> --resource-path /new-health` |
| Delete health check | `aws route53 delete-health-check --health-check-id <id>` |
| List records | `aws route53 list-resource-record-sets --hosted-zone-id <id>` |
| Change records | `aws route53 change-resource-record-sets --hosted-zone-id <id> --change-batch file://change.json` |
| Poll change status | `aws route53 get-change --id <change-id>` |
| Authoritative answer | `aws route53 test-dns-answer --hosted-zone-id <id> --record-name <fqdn> --record-type A --resolver-ip 1.1.1.1` |
| Traffic policy instance | `aws route53 get-traffic-policy-instance --id <id>` |
| CloudWatch metric (Route 53) | `aws cloudwatch get-metric-statistics --namespace AWS/Route53 --metric-name HealthCheckPercentageHealthy ...` |
| Public DNS verification | `dig @1.1.1.1 <fqdn> +short` |
| CloudWatch alarm | `aws cloudwatch describe-alarms --alarm-name-prefix <prefix>` |

## Routing-policy cheat sheet

| Policy | Use for | Failover behavior |
|---|---|---|
| **Failover** | Primary/secondary DR | Binary: PRIMARY when healthy, else SECONDARY. Requires paired records. |
| **Weighted** | Canary, blue/green, planned failover | Manual: shift weights 100/0 to 0/100. Each record can have a health check. |
| **Latency** | Multi-region active-active | Automatic: falls back to next-lowest-latency healthy region. No failover record needed. |
| **Geolocation** | Regional routing, compliance | Pair with failover SECONDARY (same geo) for regional DR. |
| **Multivalue answer** | Spreading load across many endpoints | Returns up to 8 healthy IPs (shuffled). Not load balancing. Each record can have a health check. |
| **CidrRoutingConfig (2025)** | Deterministic CIDR-based | Different answers per client CIDR block. Useful for corporate-network DR routing. |
