# Error Handling — Route 53 DNS Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance (per-layer)

### For NS_DELEGATION

Update the registrar's NS records to match the Route 53 hosted zone NS
servers. This is done at the registrar's console or API, not via the
Route 53 API (unless using Route 53 Registrar):

```bash
# If using Route 53 Registrar:
aws route53domains update-domain-nameservers \
  --domain-name <domain> \
  --nameservers Name=ns-1.awsdns.com Name=ns-2.awsdns.net \
                Name=ns-3.awsdns.org Name=ns-4.awsdns.co.uk \
  --profile <p>
```

### For DNSSEC_DS

Establish or update the DS record at the parent registrar:

```bash
# Get the DS values from the hosted zone KSK
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json | \
  jq '.KeySigningKeys[0].DS'

# If using Route 53 Registrar:
aws route53domains associate-dnssec \
  --domain-name <domain> \
  --dnssec-key <ds-values-from-above> \
  --profile <p>
```

### For DNSSEC_KSK / DNSSEC_ZSK

```bash
# Enable DNSSEC signing (generates KSK and ZSK)
aws route53 enable-dnssec --hosted-zone-id <zone-id> --profile <p>

# Disable DNSSEC signing (removes KSK and ZSK — also remove DS at parent)
aws route53 disable-dnssec --hosted-zone-id <zone-id> --profile <p>
```

### For DNS_CACHE_TTL

No CLI fix. Wait 2x the old TTL. For urgent changes, consider lowering
the TTL BEFORE making future changes (set TTL to 60 seconds, wait for
old TTL to expire, make the change).

### For ALIAS_CNAME_CONFLICT

Delete the conflicting record, then create the new one:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action": "DELETE", "ResourceRecordSet": {"Name": "<name>", "Type": "CNAME", ...}},
      {"Action": "CREATE", "ResourceRecordSet": {"Name": "<name>", "Type": "A", "AliasTarget": {...}}}
    ]
  }' --profile <p>
```

### For PHZ_VPC_ASSOCIATION

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <p>
```

For cross-account:

```bash
# In the zone account:
aws route53 create-vpc-association-authorization \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <zone-account>

# In the VPC account:
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <vpc-account>
```

### For HEALTH_CHECK

```bash
# Update the health check endpoint
aws route53 update-health-check \
  --health-check-id <hc-id> \
  --fully-qualified-domain-name <endpoint> \
  --resource-path /health \
  --port 443 \
  --type HTTPS \
  --profile <p>
```

### For RESOLVER_INBOUND

Verify the inbound endpoint SG allows UDP/TCP 53 from on-premises CIDR.
If the SG is restrictive, add an inbound rule:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol udp --port 53 \
  --cidr <on-prem-cidr> \
  --profile <p>

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp --port 53 \
  --cidr <on-prem-cidr> \
  --profile <p>
```

### For RESOLVER_OUTBOUND

Associate the resolver rule with the VPC:

```bash
aws route53resolver associate-resolver-rule \
  --resolver-rule-id <rule-id> \
  --vpc-id <vpc-id> \
  --profile <p>
```

### For WILDCARD_CERT

Delete the wildcard CNAME that intercepts ACM validation:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action": "DELETE", "ResourceRecordSet": {"Name": "*.example.com.", "Type": "CNAME", "TTL": 300, "ResourceRecords": [{"Value": "<old-target>"}]}}
    ]
  }' --profile <p>
```
