# Eval: profile-role-mapping

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — profile maps trust anchor ta-aaa111222 to role RolesAnywhereCIRunner, session duration 3600s, inline session policy restricting to s3:GetObject on my-ci-artifacts bucket

## Prompt

Create a Roles Anywhere profile in us-east-1 account
123456789012. Trust anchor ta-aaa111222 (already exists). Map
the certificate to IAM role
arn:aws:iam::123456789012:role/RolesAnywhereCIRunner. Session
duration 3600 seconds. Attach an inline session policy
restricting to s3:GetObject on arn:aws:s3:::my-ci-artifacts/*.
Name the profile ci-runner-profile. Region us-east-1.
