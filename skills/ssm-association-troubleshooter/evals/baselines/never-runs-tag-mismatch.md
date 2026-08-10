# Baseline (no-skill) response: never-runs-tag-mismatch

This file captures what a generic assistant produces WITHOUT the
ssm-association-troubleshooter skill loaded — note the absence
of the tag-key case-sensitivity detection and the structured
VERDICT that the skill adds.

---

The association is not running. Check that the schedule
expression is correct and that the targets match your instances.
The cron expression `cron(0 2 * * ? *)` looks valid.

Verify the instance has the tags the association is targeting
(Environment=prod). You may need to update the targets or retag
your instances.
