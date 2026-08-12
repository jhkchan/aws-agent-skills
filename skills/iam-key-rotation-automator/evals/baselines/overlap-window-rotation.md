# Baseline (no-skill) response: overlap-window-rotation

This file captures what a generic assistant produces WITHOUT the
iam-key-rotation-automator skill loaded.

---

The CI/CD pipeline user's key is 95 days old. You should rotate it
by creating a new key, updating the CodeBuild project to use the new
key, and then deactivating the old one.

You can keep both keys active for a while to make sure the new one
works before removing the old one. Then delete the old key after
confirming everything is fine.

Use `aws iam update-access-key` to deactivate and `aws iam
delete-access-key` to remove the old key.
