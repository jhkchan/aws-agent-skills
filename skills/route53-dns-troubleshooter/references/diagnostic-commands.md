# Diagnostic Commands — Route 53 DNS Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Account-wide pre-flight commands

```bash
# 1. List all hosted zones (public and private)
aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | {Id, Name, PrivateZone, RecordSetCount}'

# 2. Get hosted zone details (including NS and SOA records)
aws route53 get-hosted-zone --id <zone-id> --output json

# 3. List all resource record sets in the zone
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json

# 4. Get DNSSEC status for the zone
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json

# 5. Check health check status
aws route53 get-health-check-status \
  --health-check-id <hc-id> --output json

# 6. Resolver endpoints (for hybrid DNS)
aws route53resolver list-resolver-endpoints --output json

# 7. AWS Health (regional events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json

# 8. Live DNS resolution (from a public resolver)
dig +trace +additional NS <domain> @8.8.8.8
dig +dnssec +multi <domain> @8.8.8.8
```

## Step 2 — NS delegation probes

```bash
# Get the hosted zone's assigned NS servers
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "NS") | .ResourceRecords[].Value'

# Check what the TLD servers see (via a public resolver)
dig +trace +additional NS <domain> @8.8.8.8

# Check the registrar's NS records
dig NS <domain> @8.8.8.8 +short
```

## Step 3 — DNSSEC probes

```bash
# Get DNSSEC status for the zone
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json

# Check the DS record at the parent (via a public resolver)
dig +dnssec DS <domain> @8.8.8.8 +short

# Check the DNSKEY records (KSK and ZSK)
dig +dnssec DNSKEY <domain> @8.8.8.8 +short
```

## Step 4 — cache/TTL probes and interpretation

```bash
# Query the authoritative server directly (bypass all caches)
dig <domain> @<route53-ns-server> +short

# Query a public resolver
dig <domain> @8.8.8.8 +short

# Query the local system resolver
dig <domain> +short
```

If the authoritative server returns the new value but public resolvers
return the old value, the issue is TTL-based caching. Wait 2x the old
TTL. If the authoritative server returns the old value, the change was
not committed (verify with `list-resource-record-sets`).

## Step 5 — alias/CNAME conflict probes

```bash
# List existing records for the name
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Name == "<name>")'
```

## Step 7 — health check probes

```bash
aws route53 get-health-check-status \
  --health-check-id <hc-id> --output json

aws route53 get-health-check \
  --health-check-id <hc-id> --output json | \
  jq '.HealthCheckConfig'
```

## Step 8 — PHZ VPC association probes

```bash
aws route53 get-hosted-zone --id <zone-id> --output json | \
  jq '.VPCs'

aws route53 list-vpc-association-authorizations \
  --hosted-zone-id <zone-id> --output json

aws ec2 describe-dhcp-options \
  --dhcp-options-ids <dhcp-options-id> --output json | \
  jq '.DhcpOptions.DhcpConfigurations'
```

## Step 9 — split-horizon probes and interpretation

```bash
# Check for both public and private zones with the same name
aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | select(.Name == "<domain>.") | {Id, Name, PrivateZone}'
```

If both a public and a private zone exist for the same domain:
- Queries from the VPC (associated with the private zone) resolve the
  private zone's records.
- Queries from the internet resolve the public zone's records.

This is intentional for split-horizon DNS. If it is NOT intended, either
delete the private zone or rename the private zone (e.g.,
`internal.example.com`).

## Step 10 — resolver inbound probes

```bash
aws route53resolver list-resolver-endpoints \
  --filters Name=Direction,Values=INBOUND --output json

aws route53resolver get-resolver-endpoint \
  --resolver-endpoint-id <endpoint-id> --output json

# Check Security Groups on the inbound endpoint ENIs
aws ec2 describe-security-groups \
  --group-ids <sg-ids> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

## Step 11 — resolver outbound probes

```bash
aws route53resolver list-resolver-endpoints \
  --filters Name=Direction,Values=OUTBOUND --output json

aws route53resolver list-resolver-rules --output json

aws route53resolver list-resolver-rule-associations --output json
```

## Step 12 — wildcard cert probes and interpretation

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "CNAME") | select(.Name | test("_acme-challenge|^[*_]"))'

dig CNAME _<hash>.<domain> @8.8.8.8 +short
```

If a wildcard CNAME `*.example.com` exists and ACM creates a validation
CNAME `_abc123.example.com`, Route 53 returns the wildcard CNAME
instead of the validation CNAME. This prevents ACM from validating or
renewing the certificate.

Fix: delete the wildcard CNAME, or use a more specific CNAME that does
not conflict with the ACM validation record.

## Step 12b — domain transfer probes and interpretation

```bash
# Check NS records at the TLD
dig NS <domain> @8.8.8.8 +short

# Check DS record (DNSSEC) at the TLD
dig +dnssec DS <domain> @8.8.8.8 +short
```

During a domain transfer:
1. The NS records change from the old registrar's delegation to the new
   registrar's delegation.
2. If DNSSEC was enabled, the DS record must be re-established at the
   new registrar.
3. A gap between NS change and DS establishment causes SERVFAIL on
   validating resolvers.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`change-resource-record-sets`, `associate-vpc-with-hosted-zone`,
  `change-tags-for-resource`, `update-health-check`,
  `disassociate-vpc-from-hosted-zone`, DNSSEC enable/disable), emit
  and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`list-hosted-zones`, `get-hosted-zone`,
  `list-resource-record-sets`, `get-dnssec`, `get-health-check`,
  `get-health-check-status`, `list-resolver-endpoints`,
  `list-resolver-rules`, `dig`, `nslookup`). Do not perform
  state-changing operations as diagnostic probes.

- **`change-resource-record-sets`** is the primary state-changing
  command. Use UPSERT (not CREATE) to avoid failures if the record
  already exists. Always confirm the record set before applying.

- **`associate-vpc-with-hosted-zone`** enables private zone resolution
  for the VPC. If the zone name overlaps with a public zone, the
  private zone takes precedence in the VPC (split-horizon). Confirm
  this is intended.

- **DNSSEC enable/disable** is a multi-step process. Enabling DNSSEC
  generates KSK and ZSK, but the DS record must be established at the
  parent registrar separately. Disabling DNSSEC removes signing but
  leaves the DS record at the parent until explicitly removed.

- **NS record changes** at the registrar can take 24-48 hours to
  propagate through the TLD. Plan the change during a maintenance
  window and have a rollback plan (old NS values documented).

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple zones (e.g., stale DS records after
  a KSK rotation), batch remediation into groups of at most 5 zones,
  emit a single CONFIRM per batch, and verify between batches.
