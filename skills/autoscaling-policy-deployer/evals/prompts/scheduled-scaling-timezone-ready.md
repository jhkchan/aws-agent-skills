# Eval prompt: scheduled-scaling-timezone-ready

Design a deployment plan for scheduled scaling and target tracking.
Emit the standard VERDICT block (POLICY_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- ASG name: internal-tools-asg
- ASG exists, multi-AZ across 3 AZs, ELB health checks, Min=2
  Desired=3 Max=8
- Launch template: tools-template v4 (valid)
- Target tracking on ASGAverageCPUUtilization at target 50.0,
  ScaleOutCooldown 60, ScaleInCooldown 300
- Scheduled action "business-hours-scale-up": recurrence
  `0 9 * * Mon-Fri`, Min=4 Desired=6 Max=8, timezone
  America/New_York
- Scheduled action "off-hours-scale-down": recurrence
  `0 19 * * Mon-Fri`, Min=1 Desired=1 Max=8, timezone
  America/New_York
- Warm pool: Stopped, min 1, ReuseOnScaleIn true
- Region: us-east-1

Additional context: these are internal business-hours tools used by a
US-East team. Off-hours traffic is near-zero. The team wants capacity
to ramp at 9 AM ET and drop to a minimum at 7 PM ET.
