# Baseline (no-skill) response: artifact-s3-permission-denied

This file captures what a generic assistant produces WITHOUT the
codebuild-build-troubleshooter skill loaded.

---

Your CodeBuild build fails during artifact upload with "Access Denied."
This is likely an S3 permissions issue. Check that the artifacts bucket
exists and that the CodeBuild service role has permissions to write to
it. You may need to add S3 permissions to the role.

The build itself completed successfully, so the issue is just with the
artifact upload step. Also check if the bucket has a bucket policy that
might be blocking access, or if KMS encryption is causing issues.
