# Eval prompt: clean-weighted-ok

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: clean-weighted-ok
Hosted zone: Z6F7G8H9I0J1K2L3 (public, prod2.example.com)
DNSSEC: enabled (KSK active, DS published at parent)

Record sets:
  Name: api.prod2.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: primary
  Weight: 90
  TTL: 60
  ResourceRecords:
    - Value: 203.0.113.40
  HealthCheckId: hc-primary-aaa

  Name: api.prod2.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: secondary
  Weight: 10
  TTL: 60
  ResourceRecords:
    - Value: 203.0.113.41
  HealthCheckId: hc-secondary-bbb
