# Worked Examples — Auto Scaling Policy Deployer

## Worked example — PREREQUISITES_MISSING (dual-policy trap)

```text
POLICY_SPEC: prod-web-asg
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] ASG baseline: multi-AZ (3 AZs), EC2 health checks, Min=2 Desired=4 Max=10
  [✗] Scaling policy type(s): dual-policy conflict — target tracking on CPU AND step scaling on CPU; both reactive on same metric dimension
  [✓] Target tracking: ASGAverageCPUUtilization target 50.0 ScaleOutCooldown 60 ScaleInCooldown 300
  [✗] Step scaling: SAME metric (CPU) as target tracking — this is the dual-policy trap; alarms conflict, ASG oscillates. Choose a different metric or remove.
  [OPTIONAL] Scheduled scaling: not configured
  [OPTIONAL] Warm pool: not configured
  [OPTIONAL] Instance refresh: not configured
  [OPTIONAL] Advanced: capacity rebalance off | predictive off | MIP none
VERIFICATION_COMMANDS:
  aws autoscaling describe-policies --auto-scaling-group-names prod-web-asg
```
