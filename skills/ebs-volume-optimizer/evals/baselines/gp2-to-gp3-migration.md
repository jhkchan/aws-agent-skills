# Baseline (no-skill) response: gp2-to-gp3-migration

This file captures what a generic assistant produces WITHOUT the
ebs-volume-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, BurstBalance analysis, dollar
savings estimate, CONFIRM gate, pre-modification snapshot).

---

Your gp2 volume is 500 GB and the BurstBalance metric shows it's
frequently dropping to 0%, which means you're being throttled during
peak hours. You should consider migrating to gp3, which gives you 3000
IOPS baseline and is about 20% cheaper.

You can do this with:

```
aws ec2 modify-volume --volume-id vol-gp2-to-gp3-migration --volume-type gp3
```

The modification happens online so there's no downtime. Your monthly
cost should drop from around $50 to $40 per month.

You might also want to set up snapshot management since you don't have
a DLM policy configured.
