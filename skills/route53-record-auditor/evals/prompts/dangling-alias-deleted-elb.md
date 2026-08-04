# Eval prompt: dangling-alias-deleted-elb

Audit the following Route 53 record set configuration for DNS posture
exposure. Emit the standard VERDICT block (RECORD, VERDICT, REASON, RISK,
FINDINGS, REMEDIATION).

Record set id: dangling-alias-deleted-elb
Hosted zone: Z2B3C4D5E6F7G8H9 (public, app.example.com)
DNSSEC: enabled (KSK active)

Record set:
  Name: legacy.app.example.com
  Type: A
  RoutingPolicy: simple
  TTL: 300
  AliasTarget:
    DNSName: deleted-alb-9876543210.us-east-1.elb.amazonaws.com
    EvaluateTargetHealth: true
  Target status: ELB deleted (confirmed via describe-load-balancers — DNS name not found)
