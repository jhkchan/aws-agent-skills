# Baseline (no-skill) response: finding-suppression-accepted-risk

This file captures what a generic assistant produces WITHOUT the
inspector2-automation-automator skill loaded.

---

Since the legacy instance has no patch available and is scheduled
for decommission, you can suppress the finding in Inspector.

```
aws inspector2 update-finding --finding-arn arn:aws:inspector2:us-east-1:111111111111:finding/suppressed001 --status SUPPRESSED
```

Add a reason like "legacy system, decommission scheduled 2027-Q1"
so it shows up in audit trails.
