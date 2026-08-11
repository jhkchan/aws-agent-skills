# Eval prompt: dual-policy-conflict-missing

Design a deployment plan for Auto Scaling policies. Emit the standard
VERDICT block (POLICY_SPEC, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- ASG name: billing-api-asg
- ASG exists, multi-AZ across 3 AZs, ELB health checks, Min=2
  Desired=4 Max=10
- EXISTING policy: target tracking on ASGAverageCPUUtilization, target
  value 50.0, ScaleOutCooldown 60, ScaleInCooldown 300
- ADD step scaling policy on ASGAverageCPUUtilization: CloudWatch alarm
  at 70% threshold, +50% capacity adjustment via
  PercentChangeInCapacity
- The user wants BOTH policies active simultaneously for "extra
  responsiveness" under high load
- Region: us-east-1

Additional context: the operator believes layering target tracking and
step scaling on the same metric gives them tighter control. The ASG
has been oscillating between scale-out and scale-in events in pre-
production testing.
