# Baseline (no-skill) response: cfn-update-replacement-required

This file captures what a generic assistant produces WITHOUT the
cloudformation-stack-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your update failed because changing a DynamoDB table's key schema is
not allowed on an existing table. CloudFormation would need to replace
the table (delete and recreate), which is why the ChangeSet shows
`Replacement: true`.

You'll have to either create a new table with the composite key and
migrate the data, or redesign your access pattern to avoid needing
the sort key. Make sure you take a backup before doing anything.

After fixing the template, try the update again.
