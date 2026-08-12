# Baseline (no-skill) response: sts-migration-required

This file captures what a generic assistant produces WITHOUT the
iam-key-rotation-automator skill loaded.

---

The EC2 app's key is 120 days old and should be rotated. Create a new
key with `aws iam create-access-key`, update the EC2 instance's
environment variables with the new key, then deactivate and delete
the old one.

You can SSH into the instance to update the environment variables or
use SSM Session Manager to apply the new key configuration.
