# Route 53 Health Checker IPs & Regions Reference

Supplementary reference for the Route 53 Health Check Troubleshooter
skill. Loaded on-demand when a diagnostic needs health checker IP
ranges, region coverage, SG configuration guidance, or DNS failover
verification commands.

## Health checker overview

Route 53 health checkers are distributed across 15+ AWS regions
worldwide. Each health check is probed from multiple regions
simultaneously. The health check status reflects the aggregate — if
the majority of regions report failure, the health check flips to
unhealthy.

### Health checker regions

| Region | Location |
|---|---|
| us-east-1 | N. Virginia |
| us-east-2 | Ohio |
| us-west-1 | N. California |
| us-west-2 | Oregon |
| sa-east-1 | Sao Paulo |
| ca-central-1 | Canada Central |
| eu-west-1 | Ireland |
| eu-west-2 | London |
| eu-west-3 | Paris |
| eu-central-1 | Frankfurt |
| eu-north-1 | Stockholm |
| ap-south-1 | Mumbai |
| ap-northeast-1 | Tokyo |
| ap-northeast-2 | Seoul |
| ap-southeast-1 | Singapore |
| ap-southeast-2 | Sydney |
| ap-east-1 | Hong Kong |
| me-south-1 | Bahrain |
| af-south-1 | Cape Town |

### How health checker IPs work

- Route 53 health checkers use **publicly routed IPs** that are
  separate from your VPC's IP range.
- The IPs are **not published as a static list** in the standard AWS
  IP ranges JSON. They are available via the Route 53 console and the
  `get-health-check-status` API output.
- For endpoint health checks (HTTP/HTTPS/TCP), you MUST allow inbound
  traffic from these IPs in your SG/firewall.
- For calculated and CloudWatch alarm-based health checks, no inbound
  traffic is needed (they don't probe endpoints).

## Finding the health checker IPs for a specific health check

```bash
# Get the IPs probing this specific health check
aws route53 get-health-check-status \
  --health-check-id <id> --output json | \
  jq '.HealthCheckObservations[] | {Region, IPAddress, Status, StatusReport}'
```

Each observation shows:
- `Region`: the AWS region the checker is probing from.
- `IPAddress`: the specific health checker IP.
- `Status`: Success or Failure.
- `StatusReport.CheckedTime`: when the last probe ran.
- `StatusReport.StatusReport`: human-readable failure reason.

## Security group configuration for health checkers

### Option 1: Allow all inbound on the health check port (simplest)

```
Inbound rule:
  Protocol: TCP
  Port: 443 (or your health check port)
  Source: 0.0.0.0/0
```

This is the simplest approach and works when the endpoint is already
public-facing (ALB, public EC2).

### Option 2: Allow specific Route 53 health checker IP ranges

Route 53 does not publish a static CIDR block for health checkers.
The IPs change over time. To get the current IPs:

1. Query `get-health-check-status` for an active health check — the
   output lists the IPs currently probing.
2. Check the AWS Route 53 console for the health check — it shows
   the probing IPs.
3. Use AWS's published IP ranges where available.

**Note:** Because health checker IPs can change, Option 1 (allow all
on the health check port) is more maintainable. If you need to restrict
by IP, use a prefix list or update the SG rules periodically.

## DNS failover verification commands

### Check what the authoritative servers return

```bash
# Get the authoritative NS for the domain
dig NS <domain> +short

# Query the authoritative server directly
dig @<authoritative-ns> <domain> +short
dig @<authoritative-ns> <domain> A +short
```

This shows what Route 53 is actually serving RIGHT NOW. If the
authoritative server returns the secondary IP, Route 53 has flipped.
If clients still see the old IP, the issue is resolver caching (TTL).

### Check what public resolvers return

```bash
# Google DNS
dig @8.8.8.8 <domain> +short

# Cloudflare DNS
dig @1.1.1.1 <domain> +short

# Amazon Route 53 Resolver (public)
dig @205.251.198.30 <domain> +short
```

Compare these with the authoritative response. If the authoritative
server has the new record but public resolvers return the old record,
the issue is TTL caching. Wait for the TTL to expire.

### Check the TTL on the record

```bash
dig <domain> +noall +answer
# Output shows the TTL in the second column:
# example.com.    300    IN    A    1.2.3.4
```

### Trace the DNS delegation chain

```bash
dig <domain> +trace +short
```

This traces from the root servers down to the authoritative zone,
showing each step. Useful for diagnosing NS delegation issues.

## Calculated health check logic truth table

### Default (Inverted: false)

| Child A | Child B | Calculated (AND) |
|---|---|---|
| Healthy | Healthy | **Healthy** |
| Healthy | Unhealthy | **Unhealthy** |
| Unhealthy | Healthy | **Unhealthy** |
| Unhealthy | Unhealthy | **Unhealthy** |

### Inverted (Inverted: true)

| Child A | Child B | Inverted AND |
|---|---|---|
| Healthy | Healthy | **Unhealthy** (opposite) |
| Healthy | Unhealthy | **Healthy** (opposite) |
| Unhealthy | Healthy | **Healthy** (opposite) |
| Unhealthy | Unhealthy | **Healthy** (opposite) |

The `Inverted` flag is almost always a mistake when used with multiple
children. It makes the calculated check report unhealthy when ALL
children are healthy — the opposite of what operators expect.

## Health check cost model

| Feature | Cost |
|---|---|
| Standard health check (30s interval) | ~$0.50/month per health check (first 50 billed) |
| Fast health check (10s interval) | ~$2.00/month per health check (higher cost for faster probing) |
| Calculated health check | ~$0.50/month (same as standard, regardless of child count) |
| Endpoint health check with latency graphs | Included (no extra cost) |
| Health check with string matching (HTTP_STR_MATCH) | Included (no extra cost) |

Cost scales linearly with the number of health checks. For large
deployments with many endpoints, calculated health checks can reduce
cost by aggregating child checks (the calculated check itself is one
billable unit; the child checks are each separate billable units).

## Failover time calculation worksheet

```
Step 1: Health check detection time
  Detection = RequestInterval × FailureThreshold
  Example: 30s × 3 = 90 seconds

Step 2: DNS TTL caching delay
  TTL = the TTL on the DNS record
  Example: 300 seconds

Step 3: Total client-perceived failover
  Total = Detection + TTL
  Example: 90s + 300s = 390 seconds (6.5 minutes)

Step 4: Optimization options
  Option A: Lower FailureThreshold (e.g., 3 → 1)
    New detection = 30s × 1 = 30s (risk: flapping on transient errors)
  Option B: Switch to fast health check (RequestInterval 10s)
    New detection = 10s × 3 = 30s (cost: ~4x per health check)
  Option C: Lower DNS TTL (e.g., 300 → 60)
    New caching = 60s (cost: higher Route 53 query volume)
  Option D: All three
    New detection = 10s × 1 = 10s + TTL 60s = 70s total
    (highest cost, fastest failover, highest flapping risk)
```
