# Diagnostic Commands — Route 53 Health Check Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: health check state and gather-info gate — commands

```bash
# 1. Health check configuration (type, endpoint, interval, threshold)
aws route53 get-health-check \
  --health-check-id <id> --output json

# 2. Health check status (per-region, last checked, status)
aws route53 get-health-check-status \
  --health-check-id <id> --output json

# 3. List all health checks (find the relevant one)
aws route53 list-health-checks --output json

# 4. Record sets for the hosted zone (routing policy, health check assoc.)
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json

# 5. CloudWatch health check metrics (HealthCheckPercentageHealthy,
#    HealthCheckStatus, ConnectionTime, TimeToFirstByte)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Route53 \
  --metric-name HealthCheckPercentageHealthy \
  --dimensions Name=HealthCheckId,Value=<id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json

# 6. For alarm-based health checks: CloudWatch alarm state
aws cloudwatch describe-alarms \
  --alarm-names <alarm-name> --output json

# 7. DNS resolution verification (from outside the VPC)
dig +short NS <domain-name>
dig +short <domain-name>
dig +short @<authoritative-NS> <domain-name>
```

## Step 2 — endpoint health probes

```bash
aws route53 get-health-check \
  --health-check-id <id> --output json | \
  jq '.HealthCheckConfig | {Type, IPAddress, Port, FullyQualifiedDomainName, ResourcePath, RequestInterval, FailureThreshold}'

aws route53 get-health-check-status \
  --health-check-id <id> --output json | \
  jq '.HealthCheckObservations[] | {Region, IPAddress, Status, StatusReport}'
```

## Step 3 — certificate mismatch probes

```bash
aws route53 get-health-check \
  --health-check-id <id> --output json | \
  jq '.HealthCheckConfig | {Type, FullyQualifiedDomainName, EnableSNI, Port}'

# Verify the certificate served by the endpoint
openssl s_client -connect <endpoint-ip>:443 -servername <fqdn> </dev/null 2>/dev/null | \
  openssl x509 -noout -subject -ext subjectAltName
```

## Step 4 — calculated health check probes

```bash
aws route53 get-health-check \
  --health-check-id <id> --output json | \
  jq '.HealthCheckConfig | {Type, ChildHealthChecks, Inverted}'
```

## Step 5 — DNS failover routing probes

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Name == "<domain>.") | {Name, Type, RoutingPolicy, SetIdentifier, HealthCheckId, TTL}'
```

## Step 6 — DNS resolution probes

```bash
dig <domain-name> +noall +answer
dig @<authoritative-ns> <domain-name> +short
dig @8.8.8.8 <domain-name> +short
```

## Step 7 — per-region health check probes

```bash
aws route53 get-health-check-status \
  --health-check-id <id> --output json | \
  jq '.HealthCheckObservations[] | {Region, Status}'
```

## Step 8 — alarm-based health check probes

```bash
aws route53 get-health-check --health-check-id <id> --output json | \
  jq '.HealthCheckConfig | {Type, AlarmIdentifier}'
aws cloudwatch describe-alarms --alarm-names <alarm-name> --output json | \
  jq '.MetricAlarms[] | {StateValue, MetricName, Period, EvaluationPeriods, DatapointsToAlarm, Threshold, ComparisonOperator}'
```

## Step 9 — NS delegation probes

```bash
dig NS <domain-name> +short @8.8.8.8
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "NS")'
dig NS <domain-name> +trace +short
```
