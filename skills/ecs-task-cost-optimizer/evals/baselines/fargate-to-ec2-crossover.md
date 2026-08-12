# Baseline (no-skill) response: fargate-to-ec2-crossover

This file captures what a generic assistant produces WITHOUT the
ecs-task-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, Fargate-EC2 crossover
math, capacity provider strategy, CONFIRM gate, operational overhead
warning).

---

Your ECS service `svc-fargate-to-ec2-crossover` is running on Fargate
with 20 tasks at 1 vCPU and 2 GB each. At 65% CPU utilization, you're
using the resources well, but Fargate is more expensive than EC2 for
always-on workloads.

You could save money by moving to EC2-backed ECS. An m5.large instance
costs about $0.096/hour and can fit 3-4 of your tasks. With 20 tasks
you'd need about 5-7 instances, which would cost around $350-490/month
compared to the $720/month you're paying on Fargate.

You can create a capacity provider with an EC2 ASG and migrate:

```
aws ecs create-capacity-provider --name ec2-cap-provider --auto-scaling-group-provider ...
```

Just keep in mind you'll need to manage the EC2 instances (patching,
AMI updates, etc.) which is more work than Fargate.
