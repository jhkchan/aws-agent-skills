# Diagnostic Commands — s3-secure-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Step 9 — Verification commands

```bash
# BPA verification
aws s3api get-public-access-block --bucket <BUCKET>
# Expected: all 4 True

# Encryption verification
aws s3api get-bucket-encryption --bucket <BUCKET>
# Expected: SSEAlgorithm = AES256 or aws:kms

# Ownership verification
aws s3api get-bucket-ownership-controls --bucket <BUCKET>
# Expected: ObjectOwnership = BucketOwnerEnforced

# Versioning verification
aws s3api get-bucket-versioning --bucket <BUCKET>
# Expected: Status = Enabled

# Policy verification
aws s3api get-bucket-policy --bucket <BUCKET>

# Lifecycle verification
aws s3api get-bucket-lifecycle-configuration --bucket <BUCKET>
```
