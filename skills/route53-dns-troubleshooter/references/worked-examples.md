# Worked Examples — Route 53 DNS Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Malformed input — INSUFFICIENT_DATA re-prompt template

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a domain name
  and a symptom description (NXDOMAIN, wrong IP, SERVFAIL, etc.).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the domain name being
  queried, (2) the observed symptom (NXDOMAIN, wrong IP, SERVFAIL,
  intermittent), (3) the expected resolution result, and (4) for
  live diagnosis, the HostedZoneId and whether the zone is public or
  private.
```

## Worked example — DNSSEC DS record mismatch

```text
TARGET: app.example.com (zone Z3DEFGHIJKL)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: DNSSEC is enabled on the hosted zone with KSK key tag 12345,
  but the DS record at the parent zone has key tag 67890 (from a
  previous KSK rotation). Validating resolvers return SERVFAIL because
  the chain of trust is broken (Step 3).
LAYER: DNSSEC_DS
EVIDENCE:
  - Symptom: app.example.com returns SERVFAIL from Cloudflare DNS
    (1.1.1.1, validating) but resolves correctly from a non-validating
    resolver.
  - Probe: dig +dnssec DS example.com @8.8.8.8 +short returns key tag
    67890.
  - Probe: aws route53 get-dnssec returns KeySigningKeys[0].KeyTag:
    12345.
  - Passing: ZSK is active (KeyState: INACTIVE -> NSEC signing);
    NS delegation is correct (dig +trace resolves to Route 53 NS).
REMEDIATION:
  1. Update the DS record at the registrar (Route 53 Registrar) to
     match the current KSK:
     aws route53 update-domain-nameservers is NOT the right call;
     use the registrar's DNSSEC management interface or API:
     aws route53 associate-dnssec --domain-name example.com (if
     Route 53 Registrar) with the current KSK DS values.
  2. Verify after DS propagation (TLD DS TTL, typically 24 hours):
     dig +dnssec DS example.com @8.8.8.8 +short
     dig +dnssec app.example.com @1.1.1.1 (should resolve without
     SERVFAIL; check AD bit is set)
```

## Worked example — Private hosted zone VPC association

```text
TARGET: internal.example.com (zone Z4EFGHIJKLM, private)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The private hosted zone internal.example.com is not associated
  with VPC vpc-abc123. Queries from EC2 instances in vpc-abc123
  resolve the public internet instead of the private zone, returning
  NXDOMAIN for internal service names (Step 8).
LAYER: PHZ_VPC_ASSOCIATION
EVIDENCE:
  - Symptom: EC2 instances in vpc-abc123 cannot resolve
    db.internal.example.com; dig returns NXDOMAIN.
  - Probe: aws route53 get-hosted-zone --id Z4EFGHIJKLM returns
    VPCs: [] (empty — no VPC associations).
  - Probe: dig db.internal.example.com @169.254.169.253 returns
    NXDOMAIN (AmazonProvidedDNS has no private zone to answer from).
  - Passing: the record exists in the zone (confirmed via
    list-resource-record-sets); NS delegation is N/A (private zone);
    DHCP Options Set for vpc-abc123 uses AmazonProvidedDNS.
REMEDIATION:
  1. Associate the VPC with the private hosted zone:
     aws route53 associate-vpc-with-hosted-zone \
       --hosted-zone-id Z4EFGHIJKLM \
       --vpc VPCRegion=us-east-1,VPCId=vpc-abc123 \
       --profile <p>
  2. Verify from an EC2 instance in vpc-abc123:
     dig db.internal.example.com @169.254.169.253 +short
CONFIRM: Before associating the VPC, emit and await:
  "CONFIRM: About to associate vpc-abc123 with private zone
   Z4EFGHIJKLM (internal.example.com). Proceed? (yes/no)"
```
