# Baseline (no-skill) response: gp3-iops-rightsizing

This file captures what a generic assistant produces WITHOUT the
ebs-volume-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, consumed-vs-provisioned IOPS headroom
math, dollar savings estimate, CONFIRM gate).

---

Your gp3 volume is provisioned with 8,000 IOPS but you're only using
about 1,500 on average and peaking at 2,200. Since gp3 includes 3,000
IOPS in the baseline (free), you're paying for extra IOPS you don't
need.

You can reduce the provisioned IOPS back to the 3,000 baseline:

```
aws ec2 modify-volume --volume-id vol-gp3-iops-rightsizing --iops 3000
```

The baseline 3,000 IOPS gives you about 36% headroom over your peak
consumption of 2,200, which should be sufficient. You'll save about $25
per month from the IOPS reduction (5,000 extra IOPS × $0.005/IOPS/month).

Make sure to monitor VolumeQueueLength after the change to confirm
performance is still adequate.
