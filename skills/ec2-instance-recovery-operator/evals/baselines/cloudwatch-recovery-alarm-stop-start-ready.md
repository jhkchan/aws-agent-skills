# Baseline (no-skill) response: cloudwatch-recovery-alarm-stop-start-ready

This file captures what a generic assistant produces WITHOUT the
ec2-instance-recovery-operator skill loaded.

---

The instance has a system status check failure, which indicates a
hardware issue. You can recover by stopping and starting the instance:

```bash
aws ec2 stop-instances --instance-ids i-0abcdef1234567890
aws ec2 start-instances --instance-ids i-0abcdef1234567890
```

After the instance restarts, verify the status checks pass with
`describe-instance-status`. You may also want to set up a CloudWatch
alarm for automatic recovery in the future.
