# Baseline (no-skill) response: pending-deletion-7-days

This file captures what a generic assistant produces WITHOUT the
kms-key-policy-auditor skill loaded.

---

This key is scheduled for deletion in 7 days. The key policy only grants
access to the root account, which is fine.

Since the key is being deleted, you should make sure no data still depends
on it. Once the key is deleted, any data encrypted with it will be
permanently unrecoverable.

If you need to keep the key, you can cancel the deletion with
`aws kms cancel-key-deletion`.
