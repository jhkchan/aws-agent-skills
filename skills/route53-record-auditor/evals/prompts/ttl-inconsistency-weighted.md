# Eval prompt: ttl-inconsistency-weighted

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: ttl-inconsistency-weighted
Hosted zone: Z5E6F7G8H9I0J1K2 (public, deploy.example.com)
DNSSEC: enabled (KSK active, DS published)

Record sets:
  Name: app.deploy.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: stable
  Weight: 90
  TTL: 300
  ResourceRecords:
    - Value: 203.0.113.30
  HealthCheckId: hc-stable-12345

  Name: app.deploy.example.com
  Type: A
  RoutingPolicy: weighted
  SetIdentifier: canary
  Weight: 10
  TTL: 3600
  ResourceRecords:
    - Value: 203.0.113.31
  HealthCheckId: hc-canary-67890
