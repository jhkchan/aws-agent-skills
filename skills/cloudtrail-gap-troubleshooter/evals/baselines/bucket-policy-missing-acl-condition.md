# Baseline (no-skill) response: bucket-policy-missing-acl-condition

This file captures what a generic assistant produces WITHOUT the
cloudtrail-gap-troubleshooter skill loaded.

---

The trail says it's logging but no files are showing up. This is
probably a bucket policy issue. Check that the bucket policy allows
CloudTrail to write. You may need to recreate the trail from the
console so it sets up the bucket policy correctly.

Also check if the KMS key is in the right region and that the key
policy allows CloudTrail. If the bucket has Object Ownership set to
BucketOwnerEnforced, you might need to update the bucket policy.

Try restarting logging after fixing the policy.
