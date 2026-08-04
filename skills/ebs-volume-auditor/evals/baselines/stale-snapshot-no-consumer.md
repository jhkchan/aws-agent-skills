# Baseline (no-skill) response: stale-snapshot-no-consumer

This file captures what a generic assistant produces WITHOUT the
ebs-volume-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, FSR enumeration, AMI-reference
check, deletion-ordering safety).

---

This EBS snapshot was created on 2026-02-10, so it is about 6 months old.
It is encrypted and in the standard storage tier.

If the snapshot is no longer needed, you can delete it to save storage
costs:

```
aws ec2 delete-snapshot --snapshot-id snap-0ddd444stale-snapshot
```

Before deleting, check that no AMIs reference this snapshot.
