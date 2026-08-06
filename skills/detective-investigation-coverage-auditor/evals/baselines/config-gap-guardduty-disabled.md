# Baseline (no-skill) response: config-gap-guardduty-disabled

This file captures what a generic assistant produces WITHOUT the
detective-investigation-coverage-auditor skill loaded.

---

Your Detective graph is healthy with both members actively collecting data
and fresh timestamps. However, the GuardDuty detector in this region is
disabled.

GuardDuty is the primary source of security findings for Detective, so you
should enable it with `aws guardduty create-detector --enable`. Without
GuardDuty, Detective will not have security findings to investigate.
