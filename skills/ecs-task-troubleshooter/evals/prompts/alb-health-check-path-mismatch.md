# Eval prompt: alb-health-check-path-mismatch

Diagnose the following ECS task failure. Walk the health-check
diagnostic tree (Step 5 of the decision tree) and emit the standard
VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An ECS service behind an ALB has tasks RUNNING but the target group
marks them unhealthy. Tasks stop after ~90 seconds.

## Known facts

- `describe-target-groups` for the service's target group:
  - `HealthCheckPath: "/healthz"`
  - `HealthCheckPort: "traffic-port"`
  - `HealthCheckProtocol: "HTTP"`
  - `HealthCheckIntervalSeconds: 10`
  - `HealthyThresholdCount: 3`
  - `UnhealthyThresholdCount: 3`
- `describe-target-health` shows all targets with
  `State: unhealthy`, `Reason: Target.ResponseCodeMismatch`,
  `Description: "Health checks failed with these codes: [404]"`.
- `describe-task-definition` shows container port mapping 8080→8080
  (awsvpc mode).
- `describe-services` shows `healthCheckGracePeriodSeconds: 90`.
- CloudWatch Logs has GET requests to `/healthz` returning HTTP 404.
  The application defines its health endpoint at `/api/health` and
  returns 200 OK for that path.
- ECS Exec into the running container confirms
  `curl -i http://localhost:8080/api/health` returns `200 OK`.
  `curl -i http://localhost:8080/healthz` returns `404 Not Found`.

## Symptom

Targets never transition to healthy. Tasks are stopped by the
scheduler after the grace period expires.
