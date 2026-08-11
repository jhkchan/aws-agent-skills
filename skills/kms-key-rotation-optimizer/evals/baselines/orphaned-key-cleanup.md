# Baseline (no-skill) response: orphaned-key-cleanup

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, resource association check,
IRREVERSIBLE deletion warning, grant retirement before deletion, CONFIRM
gate).

---

Your KMS key alias/legacy-app-encryption has no API calls in 30 days and
no resources using it, so it's probably safe to delete. That would save
$1/month.

You can delete it with:

```
aws kms schedule-key-deletion --key-id orphaned-key-cleanup --pending-window-in-days 7
```

Make sure nothing is using it first, since KMS deletion is permanent.
