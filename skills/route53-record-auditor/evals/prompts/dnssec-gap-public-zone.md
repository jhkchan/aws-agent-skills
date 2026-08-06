# Eval prompt: dnssec-gap-public-zone

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: dnssec-gap-public-zone
Hosted zone: Z3C4D5E6F7G8H9I0 (public, prod.example.com)
DNSSEC: not enabled (no KSK or ZSK configured, KeySigningKeys array empty)

Record set:
  Name: www.prod.example.com
  Type: A
  RoutingPolicy: simple
  TTL: 300
  ResourceRecords:
    - Value: 203.0.113.10
