# Eval prompt: 504-idle-timeout-exceeded

Diagnose the 5xx failure for the following ALB. Walk the error-code-driven
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of ALB prod-reports-alb receive 504 GatewayTimeout on
POST /reports/generate after exactly 60 seconds. The report-generation
endpoint takes 75-90 seconds to complete on the target.

Load balancer: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/
  app/prod-reports-alb/mno345
Type: application (ALB)
Scheme: internet-facing
Target group: tg-reports (arn ends in /target-group/tg-reports/pqr678)
aws elbv2 describe-load-balancer-attributes prod-reports-alb:
  idle_timeout.timeout_seconds: 60
  deregistration_delay.timeout_seconds: 300
aws elbv2 describe-target-health tg-reports:
  - Target i-reports-1: State healthy
  - Target i-reports-2: State healthy
ALB access logs (S3) on failing requests:
  target_processing_time: 60.0
  error_reason: Target.Timeout
  target_status_code: - (no response received)
CloudWatch TargetResponseTime: Maximum 60.0s (capped at the idle
  timeout).
Direct curl from a bastion:
  time curl -X POST http://<target-ip>:8080/reports/generate
    → returns in 82 seconds (target succeeds when given time).
Target SG sg-target-reports: allows sg-alb-reports on tcp/8080.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
