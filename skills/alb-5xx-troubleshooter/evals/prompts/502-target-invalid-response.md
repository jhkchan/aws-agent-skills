# Eval prompt: 502-target-invalid-response

Diagnose the 5xx failure for the following ALB. Walk the error-code-driven
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of ALB prod-app-alb receive 502 BadGateway
intermittently. The target application occasionally crashes the HTTP
server process mid-response, returning a truncated HTTP response. ALB
access logs show `error_reason: Target.InvalidResponse`.

Load balancer: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/
  app/prod-app-alb/stu901
Type: application (ALB)
Scheme: internet-facing
Target group: tg-app (arn ends in /target-group/tg-app/vwx234)
aws elbv2 describe-target-health tg-app:
  - Target i-app-1: State healthy
  - Target i-app-2: State healthy
aws elbv2 describe-target-groups tg-app:
  Port: 8080
  HealthCheckPath: /health
  HealthCheckPort: 8080
  Matcher.HttpCode: 200
Target SG sg-target-app: allows sg-alb-app on tcp/8080.
ALB access logs (S3) on failing requests:
  error_reason: Target.InvalidResponse
  target_status_code: - (no valid HTTP status received)
  target_processing_time: 0.5-2.0s
Direct curl from a bastion (multiple times):
  - 1st request: curl: (18) transfer closed with outstanding read data
    remaining (truncated response)
  - 2nd request: HTTP/1.1 200 OK (success — intermittent)
  - 3rd request: curl: (56) Recv failure: Connection reset by peer
Application logs on i-app-1: segfault in the HTTP server worker process
  at the matching timestamps.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
