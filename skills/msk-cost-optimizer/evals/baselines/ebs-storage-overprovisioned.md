# Baseline (no-skill) response: ebs-storage-overprovisioned

This file captures what a generic assistant produces WITHOUT the
msk-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, KafkaDataLogsDiskUsed threshold
analysis, EBS cannot-be-decreased constraint awareness, blue/green
migration plan with auto-expand recommendation).

---

Your EBS volumes are 2 TB each but you're only using about 20% of the
disk. That's a lot of wasted storage. You could save money by using
smaller volumes, maybe 500 GB or so. Check the MSK console to see if
you can resize the volumes.
