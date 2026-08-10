# Eval prompt: 503-wrong-health-check-path

Diagnose the 5xx failure for the following ALB. Walk the error-code-driven
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of ALB prod-web-alb receive 503 ServiceUnavailable on
all paths. All targets in the tg-web target group are unhealthy. The
application was recently updated and the health endpoint moved from
`/health` to `/healthz`.

Load balancer: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/
  app/prod-web-alb/abc123
Type: application (ALB)
Scheme: internet-facing
Target group: tg-web (arn ends in /target-group/tg-web/def456)
TargetType: instance
aws elbv2 describe-target-health tg-web:
  - Target i-web-1: State unhealthy, Reason Target.FailedHealthChecks
  - Target i-web-2: State unhealthy, Reason Target.FailedHealthChecks
aws elbv2 describe-target-groups tg-web:
  HealthCheckPath: /health
  HealthCheckPort: 8080
  Matcher.HttpCode: 200
Direct curl from a bastion in the VPC:
  curl http://<target-ip>:8080/health → HTTP 404 Not Found
  curl http://<target-ip>:8080/healthz → HTTP 200 OK
Target SG sg-target-web: allows sg-alb-prod on tcp/8080 (correct).
ALB SG sg-alb-prod: attached to prod-web-alb.
ALB idle timeout: 60s.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
