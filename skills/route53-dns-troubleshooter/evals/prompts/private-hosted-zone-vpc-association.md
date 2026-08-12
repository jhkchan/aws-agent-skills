# Eval prompt: private-hosted-zone-vpc-association

Diagnose the Route 53 private hosted zone resolution failure for the
following zone and VPC. Walk the symptom-driven diagnostic tree and emit
the standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: EC2 instances in VPC `vpc-abc123` cannot resolve
`db.internal.example.com`. `dig` returns NXDOMAIN.

```text
Domain: db.internal.example.com
HostedZoneId: Z4EFGHIJKLM
PrivateZone: true

Hosted zone config (get-hosted-zone):
  VPCs: [] (empty — no VPC associations)

DHCP Options Set for vpc-abc123:
  domain-name-servers: AmazonProvidedDNS

Record in the zone (list-resource-record-sets):
  A: db.internal.example.com -> 10.0.1.50 (TTL 300)

DNS resolution test:
  dig db.internal.example.com @169.254.169.253 +short:
    (empty — NXDOMAIN; AmazonProvidedDNS has no private zone
     to answer from)
```

The private hosted zone has no VPC associations. AmazonProvidedDNS
(169.254.169.253) cannot answer queries for `internal.example.com`
because the zone is not associated with the VPC.
