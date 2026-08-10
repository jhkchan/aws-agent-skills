# Baseline (no-skill) response: asg-instance-store-blocked

This file captures what a generic assistant produces WITHOUT the
ec2-instance-recovery-operator skill loaded.

---

To recover the instance, stop and start it:

```bash
aws ec2 stop-instances --instance-ids i-0abcdef1234567890
aws ec2 start-instances --instance-ids i-0abcdef1234567890
```

Since the instance is in an Auto Scaling Group, the ASG may replace
it during the process. You may want to suspend the health check
process before stopping.
