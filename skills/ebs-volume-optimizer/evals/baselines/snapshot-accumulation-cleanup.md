# Baseline (no-skill) response: snapshot-accumulation-cleanup

This file captures what a generic assistant produces WITHOUT the
ebs-volume-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, DLM policy creation, Snapshot
Archive recommendation, dollar savings math, CONFIRM gate).

---

Your gp3 volume looks fine from a performance perspective, but you have
145 snapshots with no lifecycle policy! That's a lot of snapshot storage
cost. At roughly 500 GB per snapshot and 145 snapshots, you're storing
about 72,500 GB of snapshots at $0.05/GB which comes to around $3,625
per month just for snapshots.

You should set up a DLM policy to automatically delete old snapshots.
I'd recommend keeping 30 days of daily snapshots and deleting the rest.

You can create a DLM policy using the AWS CLI or console. For the 90
snapshots older than 90 days that haven't been restored, you could
consider archiving them to save 75% on storage costs.

You'll want to clean this up as it's costing you more than the volume
itself.
