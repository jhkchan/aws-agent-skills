# Eval prompt: target-tracking-cpu-ready

Design a deployment plan for an Auto Scaling policy. Emit the standard
VERDICT block (POLICY_SPEC, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- ASG name: prod-web-asg
- ASG exists, multi-AZ across 3 AZs, ELB health checks, Min=2
  Desired=4 Max=10
- Launch template: my-web-template v3 (valid, latest version)
- Policy: target tracking on ASGAverageCPUUtilization at target 50.0
- ScaleOutCooldown: 60, ScaleInCooldown: 300
- No other scaling policies currently attached
- Region: us-east-1
- Account: 111111111111

Additional context: this is the first scaling policy being attached to
the ASG. The application is CPU-bound (compute-heavy API).
