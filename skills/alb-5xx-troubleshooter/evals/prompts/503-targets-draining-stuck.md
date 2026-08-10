# Eval prompt: 503-targets-draining-stuck

Diagnose the 5xx failure for the following ALB. Walk the error-code-driven
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of ALB prod-deploy-alb receive 503 ServiceUnavailable
starting at 14:30 UTC after a deployment. All old targets were
deregistered simultaneously; new targets are still in `initial` state.
The deployment script deregistered the old targets before registering
the new ones.

Load balancer: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/
  app/prod-deploy-alb/yz567
Type: application (ALB)
Scheme: internet-facing
Target group: tg-deploy (arn ends in /target-group/tg-deploy/abc890)
aws elbv2 describe-target-health tg-deploy:
  - Target i-old-1: State draining
  - Target i-old-2: State draining
  - Target i-new-1: State initial
  - Target i-new-2: State initial
aws elbv2 describe-target-group-attributes tg-deploy:
  deregistration_delay.timeout_seconds: 600
  slow_start.duration_seconds: 0
Target group health check:
  HealthCheckPath: /health
  HealthCheckIntervalSeconds: 30
  HealthyThresholdCount: 5
  (time to healthy for new targets: 5 * 30s = 150s)
ALB access logs: no target_status_code on any request during the
  failure window; target:port field is "-".
CloudWatch HealthyHostCount: 0 during the failure window.
CloudWatch UnHealthyHostCount: 0 (draining targets are not counted
  as unhealthy).

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
