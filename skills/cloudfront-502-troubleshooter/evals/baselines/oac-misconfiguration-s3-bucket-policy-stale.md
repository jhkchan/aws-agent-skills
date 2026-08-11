# Baseline (no-skill) response: oac-misconfiguration-s3-bucket-policy-stale

---

Your CloudFront distribution is returning 502 errors when fetching S3
objects. This could be a permissions issue. Try:

1. Verify the S3 bucket policy allows CloudFront access.
2. Check that the Origin Access Control (OAC) is configured correctly
   in the CloudFront distribution.
3. Make sure the S3 objects exist and are accessible.
4. Review the bucket policy for any deny statements.

If you recently migrated from OAI to OAC, double-check that all
configurations were updated to reflect the new setup.
