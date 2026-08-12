# Example usage: alb-unhealthy-target-troubleshooter

A walkthrough showing the skill diagnosing a target health failure caused
by a health check path misconfiguration, demonstrating the symptom-to-layer
triage, the security-group-vs-path decision, the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict, and the path-correction remediation.

## Input (user prompt)

> Our production ALB started returning 503s at 09:15 UTC. All 6 targets
> in the target group are unhealthy. We redeployed the application last
> night — the new version moved the health endpoint from /health to
> /healthz. Help us find the root cause.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-web/abc123
TargetType: instance
HealthCheckPath: /health
HealthCheckPort: traffic-port
HealthCheckProtocol: HTTP
Matcher: { HttpCode: "200" }
Target Port: 8080
Protocol: HTTP
Targets: 6 registered, 6 unhealthy (all Reason: Target.FailedHealthChecks)

Security group sg-prod-app allows inbound from sg-prod-alb on port 8080.

Direct curl from a bastion:
  curl -s -o /dev/null -w "%{http_code}" http://10.0.1.42:8080/health → 404
  curl -s -o /dev/null -w "%{http_code}" http://10.0.1.42:8080/healthz → 200
```

## Skill output

```text
TARGET: tg-prod-web (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-web/abc123)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: All 6 targets show unhealthy with Target.FailedHealthChecks.
  The HealthCheckPath is configured as /health but the application now
  serves the health endpoint on /healthz after last night's deploy.
  A direct curl to /health returns 404 (does not match Matcher.HttpCode
  200); /healthz returns 200.
LAYER: HEALTH_CHECK_PATH
EVIDENCE:
  - Symptom: describe-target-health shows all 6 targets in state
    "unhealthy" with Reason "Target.FailedHealthChecks".
  - Probe: curl -s -o /dev/null -w "%{http_code}"
    http://10.0.1.42:8080/health returns 404 (not 200).
  - Probe: curl -s -o /dev/null -w "%{http_code}"
    http://10.0.1.42:8080/healthz returns 200.
  - Passing: security group sg-prod-app allows inbound from sg-prod-alb
    on port 8080 (SG is not the issue); HealthCheckPort is traffic-port
    so it probes port 8080 correctly (port is not the issue);
    HealthCheckProtocol is HTTP matching the application (protocol is
    not the issue).
REMEDIATION:
  1. Update the target group health check path:
     aws elbv2 modify-target-group \
       --target-group-arn arn:...:targetgroup/tg-prod-web/abc123 \
       --health-check-path /healthz
  2. Wait for HealthyThresholdCount consecutive successes (default 5
     checks at 30s interval = ~2.5 minutes).
  3. Verify with describe-target-health; all targets should transition
     to "healthy".
CONFIRM: Before updating the target group, emit and await:
  "CONFIRM: About to modify health-check-path on tg-prod-web from
   /health to /healthz. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Identified the path mismatch via direct curl evidence.** A generic
   assistant says "check if the app is running" and "check the SG." The
   skill's first probe is a direct curl to both paths, which immediately
   identifies the 404-vs-200 mismatch. The path changed during the
   deploy but the target group was not updated.

2. **Ruled out security group with positive evidence.** The skill
   confirms `sg-prod-app` allows inbound from `sg-prod-alb` on port
   8080. This eliminates the most common all-targets-unhealthy cause
   (SG blocking health checker) before recommending a fix.

3. **Ruled out port mismatch.** The `HealthCheckPort` is `traffic-port`,
   which probes the target's registered port (8080). The application
   listens on 8080. Port is not the issue.

4. **Recommended the TG-side fix, not the app-side fix.** The primary
   remediation is updating the target group's health check path to
   match the new endpoint. A generic assistant might suggest reverting
   the deploy or re-adding the old endpoint.

5. **Included the confirmation gate.** The skill emits a CONFIRM block
   before the `modify-target-group` CLI, ensuring the operator approves
   the state-changing operation.

## Slash-command invocation

```
/aws:troubleshoot-alb-unhealthy-target
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why all targets in tg-prod-web are unhealthy"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: alb-unhealthy-target-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the target health recovery:

```bash
# Confirm the health check path was updated
aws elbv2 describe-target-groups \
  --target-group-arns arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-web/abc123 \
  --query 'TargetGroups[0].HealthCheckPath' --output text

# Monitor target health recovery
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-web/abc123 \
  --output table

# Confirm UnHealthyHostCount drops to zero
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name UnHealthyHostCount \
  --dimensions Name=TargetGroup,Value=tg-prod-web \
    Name=LoadBalancer,Value=app/prod-alb/abc123 \
  --start-time $(date -d '-15 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Sum \
  --profile default --output json
```

Then monitor the ALB's `HTTPCode_Target_2XX_Count` metric for 10-15
minutes to confirm traffic is flowing to the targets.
