# Eval prompt: predictive-scaling-no-history-missing

Design a deployment plan for predictive scaling. Emit the standard
VERDICT block (POLICY_SPEC, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- ASG name: new-launch-asg
- ASG created 4 hours ago, Min=2 Desired=2 Max=8, multi-AZ across
  3 AZs, EC2 health checks
- Launch template: new-app-template v1
- Add predictive scaling on ASGCPUUtilization, TargetValue 40
- Mode: ForecastAndScale
- SchedulingBufferTime: 300
- MaxCapacityBreachBehavior: IncreaseMaxCapacity, MaxCapacityBuffer: 10
- The ASG has only 4 hours of CPU data so far (low traffic in pre-launch
  soak)
- Region: us-east-1

Additional context: the team is launching a new product and wants
predictive scaling enabled from day 1 so capacity ramps automatically
before the marketing push. They checked the ASG and it has been running
quietly for 4 hours with minimal traffic.
