# End-to-end usage scenario: autoscaling-group-auditor

A walkthrough showing the skill auditing a production ASG that has an ELB
health check with no target group attached (MISCONFIGURED), demonstrating the
infinite-replacement-loop concept, the ordered classification logic, and the
per-finding remediation workflow.

## Input (user prompt)

> Review this ASG configuration before we promote it to production. It's
> fronting our web traffic through an ALB.

```
ASG name: prod-web-asg
LaunchTemplate:
  LaunchTemplateId: lt-0abc123def456
  Version: "3"
  MetadataOptions:
    HttpTokens: required
MinSize: 2
MaxSize: 6
DesiredCapacity: 4
AvailabilityZones: [us-east-1a, us-east-1b, us-east-1c]
HealthCheckType: ELB
HealthCheckGracePeriod: 300
TargetGroupARNs: []
LoadBalancerNames: []
MixedInstancesPolicy: null
CapacityRebalance:
  Enabled: false
TerminationPolicies: [Default]
```

## Skill output

```text
ASG: prod-web-asg
VERDICT: MISCONFIGURED
REASON: HealthCheckType is ELB but no TargetGroupARNs or LoadBalancerNames
are attached — every instance will be Unhealthy from launch, creating an
infinite replacement loop (Step 3).
FINDINGS:
  - [MISCONFIGURED] ELB health check with no target group or load balancer
    attached — instances are Unhealthy from launch, ASG cycles indefinitely
    (Step 3)
  - [OK] Launch template with IMDSv2 required (Step 1)
  - [OK] Capacity bounds consistent: MinSize=2, MaxSize=6, DesiredCapacity=4
    (Step 2)
  - [OK] 3 availability zones configured (Step 7)
  - [OK] MaxSize > DesiredCapacity — scale-out headroom available (Step 8)
REMEDIATION:
  1. Attach the target group that the ALB routes to:
     aws autoscaling attach-load-balancer-target-groups \
       --auto-scaling-group-name prod-web-asg \
       --target-group-arns arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/web-tg/abc123
  2. Verify the target group health check matches the app boot time:
     aws elbv2 describe-target-groups --target-group-arns <arn>
     Ensure HealthCheckPath, HealthCheckIntervalSeconds, and
     HealthyThresholdCount are set correctly.
  3. If ELB health checks are NOT intended (e.g., background workers), switch
     to EC2 health checks:
     aws autoscaling update-auto-scaling-group \
       --auto-scaling-group-name prod-web-asg --health-check-type EC2
```

## What the skill caught that a generic assistant misses

1. **The silent infinite loop.** A generic assistant says "you might want to
   attach a target group." The skill explains that with HealthCheckType=ELB
   and no target group, every instance is marked Unhealthy from launch — the
   ASG launches, waits for the grace period, checks health, finds Unhealthy,
   terminates, and relaunches. This is an **active cost-burning loop**, not a
   passive gap. The skill classifies it as MISCONFIGURED (not CONFIG_GAP)
   because it is causing incorrect behavior right now.

2. **Grace-period lifecycle reasoning.** The skill notes that the 300s grace
   period is appropriate here (unlike a 30s grace period, which would be a
   CONFIG_GAP). It explains that the grace period counts from instance launch,
   not ELB registration — so the effective warmup budget is
   `grace - registration_delay - ELB_evaluation_time`.

3. **Ordered classification with per-dimension findings.** The verdict is
   MISCONFIGURED (worst finding), but the FINDINGS list shows which dimensions
   passed (IMDSv2, capacity bounds, AZ diversity, scale-out headroom) and which
   failed (ELB health check). This lets the operator see the full posture, not
   just the worst issue.

4. **Specific remediation with CLI.** The skill provides the exact CLI command
   to attach the target group, plus a fallback (switch to EC2 checks if ELB
   health checks are not intended). A generic assistant gives vague advice.

## Slash-command invocation

```
/aws:audit-autoscaling-group
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this ASG config before promoting to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: autoscaling-group-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the target group attachment, validate the ASG posture:

```bash
# Verify the target group is attached
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names prod-web-asg \
  --query 'AutoScalingGroups[0].TargetGroupARNs' \
  --profile default --output json

# Check that instances are now passing health checks
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names prod-web-asg \
  --query 'AutoScalingGroups[0].Instances[].HealthStatus' \
  --profile default --output json

# Verify the target group health check configuration
aws elbv2 describe-target-groups \
  --target-group-arns arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/web-tg/abc123 \
  --profile default
```

Then monitor CloudWatch for `GroupTotalInstances` stabilization (no more
cycling) for 15-30 minutes.
