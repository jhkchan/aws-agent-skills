# Eval prompt: 502-target-sg-blocks-alb

Diagnose the 5xx failure for the following ALB. Walk the error-code-driven
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of ALB prod-api-alb receive 502 BadGateway on all
requests. ALB access logs show `error_reason: Target.ConnectionFailed`
for all requests. The target group tg-api forwards on port 443 but the
health check uses port 80 (which the target SG allows).

Load balancer: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/
  app/prod-api-alb/ghi789
Type: application (ALB)
Scheme: internet-facing
Target group: tg-api (arn ends in /target-group/tg-api/jkl012)
TargetType: instance
aws elbv2 describe-target-health tg-api:
  - Target i-api-1: State healthy
  - Target i-api-2: State healthy
aws elbv2 describe-target-groups tg-api:
  Port: 443 (the forward port for actual traffic)
  HealthCheckPort: 80
  HealthCheckPath: /health
  Matcher.HttpCode: 200
aws ec2 describe-security-groups sg-target-api:
  Inbound: tcp/80 from sg-alb-prod
  (NO rule for tcp/443 — the forward port is not allowed)
ALB SG sg-alb-prod: attached to prod-api-alb.
ALB access logs (S3): error_reason: Target.ConnectionFailed on every
  request; target:port field shows i-api-x:443.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
