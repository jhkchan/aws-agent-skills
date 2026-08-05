# Baseline (no-skill) response: overpermissive-build-role

This file captures what a generic assistant produces WITHOUT the
codebuild-project-auditor skill loaded.

---

The CodeBuild service role for this project has an identity-based policy
that allows every action on every resource. This is effectively
AdministratorAccess and means the build can do anything in the account
under the role.

You should scope the role down to only the permissions the build actually
needs (S3 put to the logs bucket, CodeBuild report APIs, etc.). Consider
using CloudTrail to derive the actual API usage over 30-90 days and
replacing the wildcard policy with the observed action list.

Otherwise the project configuration itself looks reasonable —
privilegedMode is false, no plaintext secrets, SSE-KMS on S3 logs,
private VPC subnets.
