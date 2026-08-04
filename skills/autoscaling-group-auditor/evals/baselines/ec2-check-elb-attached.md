# Baseline (no-skill) response: ec2-check-elb-attached

This file captures what a generic assistant produces WITHOUT the
autoscaling-group-auditor skill loaded.

---

This ASG has a target group attached but is using EC2 health checks instead
of ELB health checks. That means it won't detect application-level failures,
only instance-level issues.

The ASG is only in one availability zone (us-east-1a), which means no
multi-AZ redundancy. You might want to add more AZs.

The max size equals the desired capacity (4), so the ASG can't scale out.
The launch template has IMDSv2 required which is good.
