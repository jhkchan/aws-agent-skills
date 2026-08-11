# Route 53 Health Check & DNS Failover Reference Guide

Supplementary reference for the Route 53 Health Check Troubleshooter
skill. Loaded on-demand when a diagnostic needs health check type
semantics, failure threshold math, calculated health check logic,
DNS failover routing policy rules, or NS delegation troubleshooting.

## Health check type matrix

| Type | Protocol | What it checks | Certificate validation | Default port |
|---|---|---|---|---|
| `HTTP` | HTTP | GET to FQDN:Port/ResourcePath; expects 2xx/3xx | No | 80 |
| `HTTPS` | HTTPS | GET to FQDN:Port/ResourcePath; expects 2xx/3xx | Yes (FQDN must match cert SAN) | 443 |
| `HTTP_STR_MATCH` | HTTP | GET + string match in response body | No | 80 |
| `HTTPS_STR_MATCH` | HTTPS | GET + string match in response body | Yes | 443 |
| `TCP` | TCP | TCP connect only (no HTTP request) | No | Configured |
| `CALCULATED` | n/a | Boolean logic over child health checks | n/a | n/a |
| `CLOUDWATCH_METRIC` | n/a | CloudWatch alarm state (ALARM = unhealthy) | n/a | n/a |

## Failure threshold math

The total detection time before a health check flips to unhealthy:

```
Detection time = RequestInterval × FailureThreshold
```

| RequestInterval | FailureThreshold | Detection time |
|---|---|---|
| 30s (standard) | 3 (default) | 90 seconds |
| 30s (standard) | 1 | 30 seconds |
| 10s (fast) | 3 | 30 seconds |
| 10s (fast) | 1 | 10 seconds (high flapping risk) |

A single success between failures resets the consecutive failure
counter. The health check must observe N failures IN A ROW.

### Total client-perceived failover time

```
Failover time = Detection time + DNS TTL
```

| Config | Detection | TTL | Total max failover |
|---|---|---|---|
| Standard HC + high TTL | 90s | 300s | 390s (6.5 min) |
| Standard HC + low TTL | 90s | 60s | 150s (2.5 min) |
| Fast HC + low TTL | 30s | 60s | 90s (1.5 min) |
| Fast HC + threshold 1 + low TTL | 10s | 60s | 70s (1.2 min) |

## Calculated health check logic

| `Inverted` | Child logic | Calculated result | Effect |
|---|---|---|---|
| `false` (default) | AND (all children healthy) | Healthy only when ALL children healthy | Failover when ANY child fails |
| `false` | OR (any child healthy — requires 1 child) | Mirrors the single child | Standard passthrough |
| `true` | AND | Healthy when NOT all children healthy (i.e., at least one unhealthy) | Failover when ALL children healthy (inverted — usually a mistake) |
| `true` | Single child | Opposite of the child | Failover when the child is healthy |

### Common calculated HC mistakes

- **Inverted flag accidentally set:** The calculated check reports
  the opposite of the expected result. Remove the `Inverted` flag.
- **AND logic with many children:** One child failure fails the
  entire set. Use OR-like logic (multiple calculated checks) for
  resilience.
- **Deleted child checks referenced:** `ChildHealthChecks` contains
  IDs of deleted health checks. Update the child list.

## DNS routing policy matrix

| Policy | How it works | Health check requirement |
|---|---|---|
| `FAILOVER` | Primary served when healthy; secondary when primary unhealthy | Primary record MUST have HealthCheckId |
| `WEIGHTED` | Traffic split by weight across records | Each weighted record should have HealthCheckId; unhealthy records are removed from rotation |
| `LATENCY` | Record with lowest latency to the DNS RESOLVER is served | Each latency record should have HealthCheckId |
| `GEOLOCATION` | Record matching the DNS RESOLVER's geographic location | Each geolocation record should have HealthCheckId |
| `GEOPROXIMITY` | Record closest to the resolver (bias adjustable) | Each record should have HealthCheckId |
| `MULTIVALUE` | Up to 8 healthy records returned randomly | Each record should have HealthCheckId; unhealthy records excluded |

### Key routing policy gotchas

- **Latency/geolocation evaluate the RESOLVER's location, not the
  client's.** A client in London using Google DNS (8.8.8.8) gets the
  record for Google's resolver location (often US).
- **WEIGHTED records without HealthCheckId always receive traffic.**
  Route 53 has no signal to remove them from rotation when the
  endpoint is down.
- **MULTIVALUE returns up to 8 healthy records.** Without health
  checks, all records are returned regardless of health.

## HTTPS certificate validation

Route 53 HTTPS health checks validate the TLS certificate against the
`FullyQualifiedDomainName`:

- The FQDN MUST appear in the certificate's Subject Alternative Name
  (SAN) list or match the Common Name (CN).
- `EnableSNI: true` sends the FQDN as the SNI hostname. Required when
  the endpoint uses SNI-based virtual hosting (multiple certs on one
  IP).
- Self-signed certificates are rejected. Use CA-signed certificates
  (ACM, Let's Encrypt, commercial CA) or switch to TCP-only health
  checks (no certificate validation).
- Expired certificates are rejected. Monitor cert expiry separately.

### Certificate troubleshooting commands

```bash
# Check what cert the endpoint serves for the health check FQDN
openssl s_client -connect <endpoint-ip>:443 -servername <fqdn> </dev/null 2>/dev/null | \
  openssl x509 -noout -subject -ext subjectAltName -dates

# Verify the ACM certificate
aws acm describe-certificate --certificate-arn <arn> --output json | \
  jq '.Certificate.{DomainName, SubjectAlternativeNames, Status, NotAfter}'
```

## Health checker IP visibility

Route 53 health checkers probe from 15+ AWS regions using publicly
routed IPs. They are NOT inside your VPC.

### Endpoint reachability matrix

| Endpoint type | Health checker can reach it? | What to do |
|---|---|---|
| Public IP (EC2, ALB public) | Yes | Ensure SG allows health checker IPs |
| Private IP only (EC2 in private subnet) | No | Front with public ALB/NLB, or use Route 53 Resolver inbound endpoint |
| ALB with public-facing SG | Yes | Add health checker IPs to SG inbound |
| NLB internal | No | Front with public NLB or use a domain that resolves publicly |
| On-premises (via Direct Connect / VPN) | Depends | Ensure health checker IPs are allowed through the VPN/DX route |

### Finding health checker IPs

Route 53 publishes the health checker IP ranges. The health check
status output (`get-health-check-status`) also shows which IPs are
probing from which regions.

```bash
aws route53 get-health-check-status --health-check-id <id> --output json | \
  jq '.HealthCheckObservations[] | {Region, IPAddress, Status}'
```

## CloudWatch alarm-based health checks

| Alarm state | Health check status | Failover triggers? |
|---|---|---|
| `OK` | Healthy | No |
| `ALARM` | Unhealthy | Yes |
| `INSUFFICIENT_DATA` | Healthy | No |

### Common alarm-based HC pitfalls

- **Alarm in INSUFFICIENT_DATA under low traffic:** Not enough
  datapoints to evaluate. The alarm never fires. Ensure the alarm
  has enough evaluation periods with actual data.
- **Alarm period too long:** The alarm takes a long time to detect
  the failure. Shorten the period (e.g., 60s instead of 300s).
- **DatapointsToAlarm > EvaluationPeriods:** Impossible to alarm.
  Fix the ratio (e.g., 2 out of 3, not 4 out of 3).
- **Alarm monitors the wrong metric:** The alarm evaluates a metric
  that does not reflect endpoint health (e.g., CPU instead of HTTP
  5xx rate).

## NS delegation troubleshooting

```bash
# Check NS at the parent zone (via public resolver)
dig NS <domain> +short @8.8.8.8

# Check NS at the hosted zone
aws route53 list-resource-record-sets --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "NS") | .ResourceRecords'

# Trace the delegation chain
dig NS <domain> +trace +short
```

### NS delegation failure patterns

| Pattern | Cause | Fix |
|---|---|---|
| Parent NS != hosted zone NS | Delegation mismatch | Update parent zone NS to match hosted zone |
| Glue records missing | Subdomain NS without glue A records | Add glue A records for the subdomain NS |
| NS records recently changed | Propagation in progress (up to 48h) | Lower NS TTL before changes; wait for propagation |
| Hosted zone suspended | Zone is not active | Reactivate the zone or migrate to a new one |
| Domain registration expired | Registrar deactivated the domain | Renew the domain registration |

## DNS TTL reference

| TTL | Failover speed | Query cost | Use case |
|---|---|---|---|
| 60s | Fast (1 min max stale) | Higher (more queries) | Failover-critical records |
| 300s (default) | Medium (5 min max stale) | Moderate | Standard web apps |
| 3600s (1 hour) | Slow (1 hour max stale) | Lower | Static content, rarely changing records |
| 86400s (1 day) | Very slow (1 day max stale) | Lowest | Legacy/infrastructure records |

For failover-critical records, 60 seconds is the practical minimum.
Below 60 seconds, some recursive resolvers enforce their own minimum
TTL (often 30-60 seconds).
