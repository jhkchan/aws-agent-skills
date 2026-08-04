# Eval prompt: weighted-no-healthcheck

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: weighted-no-healthcheck
Hosted zone: Z4D5E6F7G8H9I0J1 (public, canary.example.com)
DNSSEC: enabled (KSK active, DS published)

Record sets:
  Name: svc.canary.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: blue
  Weight: 50
  TTL: 60
  ResourceRecords:
    - Value: 203.0.113.20
  (no HealthCheckId)

  Name: svc.canary.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: green
  Weight: 50
  TTL: 60
  ResourceRecords:
    - Value: 203.0.113.21
  (no HealthCheckId)
