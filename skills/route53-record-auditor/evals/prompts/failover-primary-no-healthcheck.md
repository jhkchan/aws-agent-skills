# Eval prompt: failover-primary-no-healthcheck

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: failover-primary-no-healthcheck
Hosted zone: Z1A2B3C4D5E6F7G8 (public, example.com)
DNSSEC: enabled (KSK active, DS record published at parent)

Record set:
  Name: api.example.com
  Type: A
  RoutingPolicy: failover
  SetIdentifier: primary
  Failover: PRIMARY
  TTL: 60
  AliasTarget:
    DNSName: internal-alb-1234567890.us-east-1.elb.amazonaws.com
    EvaluateTargetHealth: false
  (no HealthCheckId)
