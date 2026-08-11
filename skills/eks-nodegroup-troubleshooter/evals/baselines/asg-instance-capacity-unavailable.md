# Baseline (no-skill) response: asg-instance-capacity-unavailable

This file captures what a generic assistant produces WITHOUT the
eks-nodegroup-troubleshooter skill loaded.

---

Your node group can't scale because the ASG is getting
InsufficientInstanceCapacity errors. This means AWS doesn't have
enough m5.large instances available in us-east-1a. You should try
using a different instance type or launching in a different
availability zone.

Also check if the ASG configuration is correct and if there are any
service quota limits that might be preventing new instances. You
might want to try scaling during off-peak hours when capacity is
more likely to be available.
