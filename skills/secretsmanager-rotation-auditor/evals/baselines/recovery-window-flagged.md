# Baseline (no-skill) response: recovery-window-flagged

> This file captures what a generic assistant produces WITHOUT the
> secretsmanager-rotation-auditor skill loaded. The baseline may note
> the deletion date but misses the structured DELETION_FLAG, the recovery
> window semantics (irrecoverable after purge), and the restore-vs-verify
> decision tree.

---

This API token secret has no rotation enabled and is scheduled for deletion
on August 12th. The secret hasn't been rotated since it was created.

Since it's already marked for deletion, you should verify that no
applications are using this Stripe API key before the deletion date. If
any workload depends on it, restore the secret.

If the deletion is intentional, no rotation remediation is needed since
the secret will be permanently deleted soon.
