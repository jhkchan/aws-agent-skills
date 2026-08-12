# DNS Validation and CAA Records — ACM Certificate Monitor Operator

Deep reference on DNS validation record verification, CAA record
conflict detection and resolution, validation record lifecycle, and
DNS troubleshooting for ACM certificates. Loaded on demand by the
skill — kept out of the main SKILL.md body so the monitoring
procedure stays scannable.

## DNS validation record fundamentals

### How ACM DNS validation works

When you request a DNS-validated ACM certificate, ACM provides a CNAME
record that you must add to your DNS configuration. ACM uses this
record to verify domain ownership.

```text
ACM-provided validation CNAME:
  Name:  _abc123def456.www.example.com.
  Value: _xyz789.acm-validations.aws.

ACM periodically queries this CNAME. When it resolves correctly:
  → Domain validation: SUCCESS
  → Certificate status: ISSUED
  → The record MUST remain in DNS for renewal
```

### Why validation records must persist

A common misconception is that the validation CNAME can be removed
after the certificate is issued. This is WRONG. ACM re-validates the
domain during renewal by querying the same CNAME record. If the
record is missing:

```text
Renewal flow with missing CNAME:
  1. ACM attempts renewal (60 days before expiry)
  2. ACM queries the validation CNAME
  3. CNAME not found in DNS
  4. Renewal status: FAILED
  5. DaysToExpiry continues decreasing
  6. Certificate expires without renewal
  7. Production outage
```

### Retrieve validation records from ACM

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --query 'Certificate.DomainValidationOptions[*].{
    Domain: DomainName,
    Status: ValidationStatus,
    Method: ValidationMethod,
    CNAMEName: ResourceRecord.Name,
    CNAMEValue: ResourceRecord.Value
  }' \
  --region us-east-1 --output table
```

### Verify CNAME exists in DNS

```bash
# Using dig
dig _abc123def456.www.example.com CNAME +short
# Expected: _xyz789.acm-validations.aws.

# Using nslookup
nslookup -type=CNAME _abc123def456.www.example.com
# Expected: canonical name = _xyz789.acm-validations.aws.

# Using host
host -t CNAME _abc123def456.www.example.com
```

### Verify in Route53

```bash
ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name example.com \
  --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

aws route53 list-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --query "ResourceRecordSets[?Type=='CNAME']" \
  --output table
```

### Common DNS validation issues

1. **Trailing dot in CNAME name.** DNS records end with a trailing
   dot (`.`). Route53 adds it automatically; other DNS providers may
   not. A missing trailing dot can cause validation to fail.

2. **CNAME in wrong zone.** For `www.example.com`, the CNAME goes in
   the `example.com` zone. Putting it in the wrong zone is invisible
   but breaks validation.

3. **CNAME conflicts with existing records.** If an A record exists
   for the same name as the validation CNAME, DNS resolution may fail.
   Remove the conflicting record.

4. **DNS propagation delay.** After adding the CNAME, propagation can
   take minutes to hours depending on TTL. ACM retries validation
   automatically.

## CAA record fundamentals

### What CAA records do

CAA (Certification Authority Authorization, RFC 8659) records allow
domain owners to specify which Certificate Authorities are allowed to
issue certificates for their domain. CAs (including ACM's underlying
CA) MUST check CAA records before issuing or renewing a certificate.

### CAA record format

```text
CAA record format:
  <flags> <tag> "<value>"

Flags:
  0 = non-critical (issuer must understand the tag but can ignore if not supported)
  128 = critical (issuer MUST understand the tag or refuse to issue)

Tags:
  issue = authorize a CA to issue certificates for this domain
  issuewild = authorize a CA to issue wildcard certificates
  iodef = specify where to report violation incidents

Examples:
  0 issue "amazon.com"           → Amazon can issue certs
  0 issue "letsencrypt.org"      → Let's Encrypt can issue certs
  0 issue ";"                    → NO CA can issue (block all)
  0 issuewild "amazon.com"       → Amazon can issue wildcard certs
  0 iodef "mailto:admin@example.com" → Report incidents to this email
```

### CAA record resolution rules

CAA records are checked at multiple levels:

```text
Certificate request for www.example.com:
  1. Check CAA for www.example.com
     ├── If found → use these records
     └── If not found → continue to parent

  2. Check CAA for example.com
     ├── If found → use these records
     └── If not found → continue to parent

  3. Check CAA for com (TLD)
     ├── If found → use these records
     └── If not found → no restriction (any CA can issue)
```

**Key implication:** a CAA record on `example.com` applies to ALL
subdomains (`www.example.com`, `api.example.com`, etc.) unless a more
specific CAA record exists for the subdomain.

### CAA scenarios and ACM impact

| Scenario | CAA records | ACM impact | Fix |
|---|---|---|---|
| No CAA records | (none) | No restriction — ACM OK | None needed |
| ACM authorized | `0 issue "amazon.com"` | ACM OK | None needed |
| Multiple CAs authorized | `0 issue "amazon.com"; 0 issue "letsencrypt.org"` | ACM OK | None needed |
| ACM NOT authorized | `0 issue "letsencrypt.org"` (no amazon.com) | ACM BLOCKED | Add `0 issue "amazon.com"` |
| All blocked | `0 issue ";"` | ACM BLOCKED | Remove or replace with amazon.com |
| Wildcard OK | `0 issuewild "amazon.com"` | Wildcard ACM OK; non-wildcard needs `issue` | Add both issue and issuewild |

### Detect CAA conflicts

```bash
# Query CAA records for the domain and parent
dig example.com CAA +short
dig www.example.com CAA +short

# Comprehensive CAA check (all relevant levels)
for DOMAIN in www.example.com example.com com; do
  echo "=== CAA for $DOMAIN ==="
  dig "$DOMAIN" CAA +short
done

# Using Google DNS for external verification
dig @8.8.8.8 example.com CAA +short
```

### Fix CAA conflict in Route53

```bash
ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name example.com \
  --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

# Option 1: Add amazon.com alongside existing CAA records
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "example.com",
          "Type": "CAA",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "0 issue \"amazon.com\""},
            {"Value": "0 issue \"letsencrypt.org\""},
            {"Value": "0 iodef \"mailto:admin@example.com\""}
          ]
        }
      }
    ]
  }'

# Option 2: Remove restrictive CAA entirely (allow all CAs)
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {
        "Action": "DELETE",
        "ResourceRecordSet": {
          "Name": "example.com",
          "Type": "CAA",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "0 issue \"letsencrypt.org\""}
          ]
        }
      }
    ]
  }'
```

### CAA fix verification

After updating CAA records, wait for DNS propagation (check TTL, then
verify externally):

```bash
# Verify via Google DNS (external resolver)
dig @8.8.8.8 example.com CAA +short
# Expected: 0 issue "amazon.com"

# Verify via Cloudflare DNS
dig @1.1.1.1 example.com CAA +short

# After CAA is fixed, ACM will retry renewal automatically
# Check renewal status after ~30 minutes
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --query 'Certificate.RenewalSummary' \
  --region us-east-1
```

### ACM CAA-restricted domains

Some domains have CAA restrictions at the TLD level. For example,
certain TLDs may require CAA records that include specific CAs. If
ACM cannot issue for a domain due to TLD-level CAA, contact the
domain registrar.

## Validation record lifecycle

```text
Certificate lifecycle with DNS validation:

  1. Certificate requested
     → ACM provides validation CNAME
     → Status: PENDING_VALIDATION

  2. Operator adds CNAME to DNS
     → ACM queries CNAME
     → Status: PENDING_VALIDATION (waiting for DNS propagation)

  3. CNAME resolves correctly
     → ACM validates domain
     → Status: ISSUED

  4. Certificate in use (attached to ALB/CloudFront/etc.)
     → RenewalEligibility: INELIGIBLE (not yet in window)

  5. ~60 days before expiry
     → RenewalEligibility: ELIGIBLE
     → ACM begins renewal
     → ACM re-checks validation CNAME and CAA records

  6a. CNAME present, CAA OK
      → Renewal status: SUCCESS
      → New certificate issued, DaysToExpiry resets

  6b. CNAME missing or CAA conflict
      → Renewal status: FAILED
      → DaysToExpiry keeps decreasing
      → Operator must fix DNS/CAA before expiry
```

**Critical:** the validation CNAME and CAA records must be present
at ALL times, not just during initial validation. ACM re-checks them
during every renewal attempt.
