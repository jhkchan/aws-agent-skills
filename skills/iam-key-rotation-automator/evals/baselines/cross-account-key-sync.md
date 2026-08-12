# Baseline (no-skill) response: cross-account-key-sync

This file captures what a generic assistant produces WITHOUT the
iam-key-rotation-automator skill loaded.

---

For cross-account key rotation, you need to rotate the key in Account
A and then update the application in Account B with the new key.

Create a new key in Account A with `aws iam create-access-key`. Then
update the Secrets Manager secret in Account B with the new key
credentials.

After verifying the new key works, deactivate and delete the old key
in Account A.

You might need to assume a role in Account B to update the secret
there.
