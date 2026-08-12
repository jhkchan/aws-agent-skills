# Baseline (no-skill) response: break-glass-exception

This file captures what a generic assistant produces WITHOUT the
iam-key-rotation-automator skill loaded.

---

The key is a year old and should definitely be rotated. You can
create a new key, update whatever uses it, then deactivate and delete
the old one.

Since the operator wants it rotated immediately, go ahead and run
`aws iam create-access-key --user-name break-glass-admin`.

After updating the application, delete the old key with
`aws iam delete-access-key`.
