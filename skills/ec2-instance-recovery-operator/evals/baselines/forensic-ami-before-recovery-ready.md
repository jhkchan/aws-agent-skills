# Baseline (no-skill) response: forensic-ami-before-recovery-ready

This file captures what a generic assistant produces WITHOUT the
ec2-instance-recovery-operator skill loaded.

---

To create an AMI from the instance for forensic purposes:

```bash
aws ec2 create-image \
  --instance-id i-0abcdef1234567890 \
  --name forensic-i-0abcdef-$(date +%Y%m%d%H%M%S) \
  --no-reboot
```

After the AMI is created, you can use it to launch a recovery instance
or as a backup before attempting other recovery steps.
