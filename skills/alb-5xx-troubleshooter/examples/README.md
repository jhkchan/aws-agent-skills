# Example usage: alb-5xx-troubleshooter

A walkthrough showing the skill diagnosing a 503 that masquerades as a
target application failure, demonstrating the error-code-driven probe
order, the health check path investigation, and the evidence-backed
ROOT_CAUSE_FOUND verdict.

## Input (user prompt)

> Our web ALB started returning 503 ServiceUnavailable on all paths
> after the last application deployment. The application team says
> their code is fine — health checks were passing before the deploy.
> We've been debugging this as a target application crash for 25
> minutes. Help us find the actual root cause.

```text
Load balancer: prod-web-alb (ALB, internet-facing)
Target group: tg-web (instance-type, port 8080)
aws elbv2 describe-target-health tg-web:
  - i-web-1: State unhealthy, Reason Target.FailedHealthChecks
  - i-web-2: State unhealthy, Reason Target.FailedHealthChecks
aws elbv2 describe-target-groups tg-web:
  HealthCheckPath: /health
  HealthCheckPort: 8080
  Matcher.HttpCode: 200
Direct curl from a bastion in the VPC:
  curl http://<target-ip>:8080/health → HTTP 404 Not Found
  curl http://<target-ip>:8080/healthz → HTTP 200 OK
Target SG sg-target-web: allows sg-alb-prod on tcp/8080.
ALB idle timeout: 60s.
```

## Skill output

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-web-alb/abc123 / target-group/tg-web/def456
VERDICT: ROOT_CAUSE_FOUND
REASON: The target group health check path /health returns 404 on all
  targets — the application moved its health endpoint to /healthz in
  the last deployment. All targets are marked unhealthy, and the ALB
  has no healthy target for incoming requests (Step 3a).
LAYER: TARGET_HEALTH_CHECK
EVIDENCE:
  - Symptom: clients receive 503 ServiceUnavailable on all paths. ALB
    access logs show target_group_arn for tg-web but no
    target_status_code (no target was selected).
  - Probe: aws elbv2 describe-target-health --target-group-arn tg-web
    returns all targets State: unhealthy, Reason:
    Target.FailedHealthChecks.
  - Probe: aws elbv2 describe-target-groups --target-group-arns tg-web
    returns HealthCheckPath: /health, Matcher.HttpCode: 200.
  - Probe: curl from bastion to target on /health returns 404. curl to
    /healthz returns 200. The application moved its health endpoint;
    the health check was never updated.
  - Passing: target SG sg-target-web allows sg-alb-prod on tcp/8080
    (correct); ALB idle timeout is 60s (irrelevant — targets are not
    even being selected); listener default action correctly points to
    tg-web; no WAF associated; deregistration delay is 300s (targets
    are not draining — they are genuinely unhealthy).
REMEDIATION:
  1. Update the target group health check path to /healthz:
     aws elbv2 modify-target-group --target-group-arn <tg-web>
       --health-check-path /healthz --profile <p>
  2. Wait for healthy_threshold_count (default 3-5) consecutive
     successful checks at HealthCheckIntervalSeconds (default 30s).
     Expected time to healthy: 90-150 seconds.
  3. Verify: describe-target-health shows State: healthy for all
     targets; clients no longer see 503.
CONFIRM: Before modifying the target group, emit and await:
  "CONFIRM: About to modify-target-group on tg-web (health-check-path
   /health → /healthz). This re-evaluates health on ALL targets.
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **The health check path, not the application code.** A generic
   assistant sees "all targets unhealthy" and concludes "the
   application is crashing." The skill recognises that health check
   failures do NOT mean the application is down — the health check
   endpoint itself may have moved. The probe is a direct `curl` to the
   configured path AND an alternate path, not a log scan.

2. **The deployment correlation.** The skill connects "the failure
   started after the last deployment" to "the health endpoint moved."
   Application deployments frequently change route paths without
   updating the target group health check — a silent configuration
   drift that produces a full outage.

3. **Evidence-backed verdict.** The skill produces a positive failing
   probe (`curl /health → 404`, `curl /healthz → 200`) AND passing
   probes (target SG, idle timeout, listener rules, WAF). A generic
   assistant asserts "fix the health check" without evidence; an
   operator who instead restarts the targets loses another 25 minutes.

4. **The timing estimate.** The skill includes the expected time to
   recovery (90-150 seconds for 3-5 health checks at 30s intervals).
   This lets the operator communicate an ETA to stakeholders rather
   than saying "we're working on it."

## Slash-command invocation

```
/aws:troubleshoot-alb-5xx
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why the prod-web ALB returns 503 on all paths"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: alb-5xx-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the target health:

```bash
# Confirm the health check path is updated
aws elbv2 describe-target-groups --target-group-arns <tg-arn> \
  --profile default --output json | \
  jq '.TargetGroups[0].HealthCheckConfig.HealthCheckPath'
# Expect: "/healthz"

# Wait for targets to become healthy (poll every 30s)
aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --profile default --output json | \
  jq '.TargetHealthDescriptions[].TargetHealth.State'
# Expect: "healthy" for all targets within 90-150 seconds
```

Then monitor the CloudWatch `HTTPCode_ELB_5XX_Count` and
`HealthyHostCount` metrics for 15-30 minutes to confirm the 503 count
drops to zero and the healthy host count returns to expected.
