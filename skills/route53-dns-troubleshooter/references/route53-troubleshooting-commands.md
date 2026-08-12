# Route 53 Troubleshooting Commands Reference

Supplementary reference for the Route 53 DNS Troubleshooter skill.
Loaded on-demand when a diagnostic needs the exact CLI commands for
probing hosted zone configuration, DNSSEC status, health checks,
resolver endpoints, and VPC associations.

## Hosted zone inspection

### List all hosted zones

```bash
aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | {Id, Name, PrivateZone, RecordSetCount}'
```

### Get hosted zone details (including VPC associations)

```bash
aws route53 get-hosted-zone --id <zone-id> --output json
```

### List all resource record sets

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json
```

### List NS records for a zone

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "NS")'
```

### List SOA record

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "SOA")'
```

## DNSSEC inspection

### Get DNSSEC status for a zone

```bash
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json
```

### Check DS record at parent (via public resolver)

```bash
dig +dnssec DS <domain> @8.8.8.8 +short
```

### Check DNSKEY records

```bash
dig +dnssec DNSKEY <domain> @8.8.8.8 +short
```

### Verify DNSSEC validation with AD bit

```bash
dig +dnssec <domain> @1.1.1.1 | grep -E "status| ad:"
```

## Health check inspection

### Get health check configuration

```bash
aws route53 get-health-check \
  --health-check-id <hc-id> --output json | \
  jq '.HealthCheckConfig'
```

### Get health check status

```bash
aws route53 get-health-check-status \
  --health-check-id <hc-id> --output json
```

### List all health checks

```bash
aws route53 list-health-checks --output json | \
  jq '.HealthChecks[] | {Id, HealthCheckConfig: {Type,
    FullyQualifiedDomainName, IPAddress, Port, ResourcePath}}'
```

## Private hosted zone VPC associations

### Check VPC associations for a zone

```bash
aws route53 get-hosted-zone --id <zone-id> --output json | \
  jq '.VPCs'
```

### List VPC association authorizations

```bash
aws route53 list-vpc-association-authorizations \
  --hosted-zone-id <zone-id> --output json
```

### Check DHCP Options Set for a VPC

```bash
VPC_DHCP=$(aws ec2 describe-vpcs --vpc-ids <vpc-id> --output json | \
  jq -r '.Vpcs[0].DhcpOptionsId')

aws ec2 describe-dhcp-options \
  --dhcp-options-ids $VPC_DHCP --output json | \
  jq '.DhcpOptions.DhcpConfigurations'
```

## Resolver endpoint inspection

### List resolver endpoints

```bash
aws route53resolver list-resolver-endpoints --output json | \
  jq '.ResolverEndpoints[] | {Id, Direction, Status, Name,
    IpAddressCount}'
```

### Get resolver endpoint details

```bash
aws route53resolver get-resolver-endpoint \
  --resolver-endpoint-id <endpoint-id> --output json
```

### List resolver rules

```bash
aws route53resolver list-resolver-rules --output json | \
  jq '.ResolverRules[] | {Id, DomainName, RuleType,
    TargetIps, Status}'
```

### List resolver rule associations

```bash
aws route53resolver list-resolver-rule-associations --output json | \
  jq '.ResolverRuleAssociations[] | {ResolverRuleId, VPCId, Status,
    Name}'
```

## DNS query logging

### List query logging configurations

```bash
aws route53 list-query-logging-configs --output json | \
  jq '.QueryLoggingConfigs[] | {Id, HostedZoneId,
    CloudWatchLogsLogGroupArn}'
```

### Filter query logs in CloudWatch

```bash
aws logs filter-log-events \
  --log-group-name <log-group-name> \
  --start-time $(date -d '-1 hour' +%s)000 \
  --filter-pattern '"NXDOMAIN" OR "SERVFAIL"' \
  --output json
```

## CloudTrail lookup

### Find Route 53 API calls

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=route53.amazonaws.com \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json
```

## AWS Health

### Check for regional Route 53 events

```bash
aws health describe-events \
  --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json | \
  jq '.events[] | select(.service == "ROUTE53")'
```

## Live DNS resolution (dig / nslookup)

### Full delegation trace

```bash
dig +trace +additional NS <domain> @8.8.8.8
```

### Query a specific resolver

```bash
dig <domain> @8.8.8.8 +short
dig <domain> @1.1.1.1 +short
dig <domain> @169.254.169.253 +short
```

### Query with DNSSEC

```bash
dig +dnssec +multi <domain> @8.8.8.8
```

### Query the authoritative server directly

```bash
dig <domain> @ns-1.awsdns.com +short
```

### Query specific record type

```bash
dig A <domain> +short
dig AAAA <domain> +short
dig CNAME <domain> +short
dig MX <domain> +short
dig TXT <domain> +short
dig NS <domain> +short
dig SOA <domain> +short
```

### Check EDNS Client Subnet (for geolocation / latency)

```bash
dig +subnet=1.2.3.4/32 <domain> @8.8.8.8 +short
```

## State-changing commands (require CONFIRM gate)

### Change resource record sets

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action": "UPSERT", "ResourceRecordSet": {
        "Name": "<name>",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<ip>"}]
      }}
    ]
  }' --profile <p>
```

### Associate VPC with private hosted zone

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <p>
```

### Enable DNSSEC signing

```bash
aws route53 enable-dnssec --hosted-zone-id <zone-id> --profile <p>
```

### Disable DNSSEC signing

```bash
aws route53 disable-dnssec --hosted-zone-id <zone-id> --profile <p>
```

### Update health check

```bash
aws route53 update-health-check \
  --health-check-id <hc-id> \
  --fully-qualified-domain-name <endpoint> \
  --resource-path /health \
  --port 443 \
  --type HTTPS \
  --profile <p>
```

### Update domain nameservers (Route 53 Registrar)

```bash
aws route53domains update-domain-nameservers \
  --domain-name <domain> \
  --nameservers Name=ns-1.awsdns.com Name=ns-2.awsdns.net \
                Name=ns-3.awsdns.org Name=ns-4.awsdns.co.uk \
  --profile <p>
```

### Associate resolver rule with VPC

```bash
aws route53resolver associate-resolver-rule \
  --resolver-rule-id <rule-id> \
  --vpc-id <vpc-id> \
  --profile <p>
```
