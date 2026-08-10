# Baseline (no-skill) response: diagnose-kernel-panic-blocked

This file captures what a generic assistant produces WITHOUT the
ec2-instance-recovery-operator skill loaded.

---

The console output shows a kernel panic from the `xyz-driver` module.
The instance is running but the OS is hung. You should try rebooting
the instance:

```bash
aws ec2 reboot-instances --instance-ids i-0abcdef1234567890
```

If the reboot does not help, you may need to stop and start the
instance. You can also try connecting via Session Manager after the
reboot to investigate the module issue.
