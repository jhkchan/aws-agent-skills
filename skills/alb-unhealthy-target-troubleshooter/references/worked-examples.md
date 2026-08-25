# Worked Examples — ALB Unhealthy Target Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## INSUFFICIENT_DATA re-prompt (malformed input)

```text
TARGET: <target-group-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context -- at minimum a symptom
  description (the target health state or observed behaviour) and the
  TargetGroupArn.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact target health
  state (describe-target-health output), (2) the TargetGroupArn, and
  (3) the target group configuration (describe-target-groups output).
```

## INSUFFICIENT_DATA fallback (no positive root-cause match)

If none of the above produced a positive root-cause match, emit:

```text
TARGET: <target-group-arn>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a
  single root cause from the diagnostic tree. List the probes already
  executed and their results, and request additional context.
LAYER: UNKNOWN
EVIDENCE:
  - <probes executed and results>
  - <missing information needed>
REMEDIATION: Provide (1) the full describe-target-health output,
  (2) the full describe-target-groups output, (3) the target security
  group rules, (4) the ALB security group and subnets, and (5) the
  application's health endpoint response (curl from within the VPC).
```

## Worked example -- security group blocking health checks

```text
TARGET: tg-prod-api (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-prod-api/def456)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: All 4 targets show unhealthy with Target.ConnectionFailed.
  The target security group sg-app-443 allows inbound on port 443
  from 10.0.0.0/8 but NOT from the ALB security group sg-alb (which
  is in a different VPC CIDR). Health check port is 443; the ALB
  health checker IP is in 172.16.x.x, which is not allowed by the
  target SG ingress rule.
LAYER: SG_BLOCKING_HEALTH_CHECK
EVIDENCE:
  - Symptom: describe-target-health shows all 4 targets in state
    "unhealthy" with Reason "Target.ConnectionFailed".
  - Probe: describe-security-groups on sg-app-443 shows inbound rule
    allowing 10.0.0.0/8 on port 443, but ALB ENI IPs are in
    172.16.1.x (confirmed via describe-network-interfaces).
  - Probe: curl from an EC2 instance in the ALB subnet to a target
    on port 443 times out (connection refused).
  - Passing: HealthCheckPath /api/health returns 200 when curled
    directly from a host in the target subnet (path is correct);
    application process is running on all targets.
REMEDIATION:
  1. Add an ingress rule to the target SG allowing the ALB SG:
     aws ec2 authorize-security-group-ingress \
       --group-id sg-app-443 \
       --ip-permissions \
       IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=sg-alb}]
  2. Wait 10-30 seconds for propagation, then verify with
    describe-target-health; targets should transition to healthy.
CONFIRM: Before modifying the security group, emit and await:
  "CONFIRM: About to add ingress rule to sg-app-443 allowing sg-alb
   on port 443. Proceed? (yes/no)"
```

## Worked example -- Lambda target group unhealthy

```text
TARGET: tg-lambda-processor (arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-lambda-processor/ghi789)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Lambda target function fn-alb-processor times out on
  health check invocations. The function Timeout is 3 seconds; the
  ALB health check is a synchronous invoke that triggers the full
  handler, which takes 5-8 seconds due to a database query.
LAYER: LAMBDA_TARGET_INTEGRATION
EVIDENCE:
  - Symptom: describe-target-health shows the Lambda target in state
    "unhealthy" with Reason "Target.FailedHealthChecks".
  - Probe: aws logs filter-log-events on /aws/lambda/fn-alb-processor
    shows "Task timed out after 3.00 seconds" on health check
    invocations.
  - Probe: get-function-configuration shows Timeout: 3, Runtime:
    nodejs20.x.
  - Passing: function succeeds on non-health invocations that take
    < 3s; no errors in the function code.
REMEDIATION:
  1. Raise the Lambda function Timeout to 10 seconds:
     aws lambda update-function-configuration \
       --function-name fn-alb-processor --timeout 10
  2. Alternatively, add a fast-path in the handler that returns 200
    immediately for health check requests (detect via event path or
    HTTP method), avoiding the database query.
  3. Verify with describe-target-health after the next health check
    cycle; target should show "healthy".
CONFIRM: Before updating the function configuration, emit and await:
  "CONFIRM: About to raise fn-alb-processor timeout to 10s. Proceed?
   (yes/no)"
```
