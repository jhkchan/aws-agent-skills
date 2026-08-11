# Eval: revoked-profile-impact

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — revocation playbook: remove ARN from CSC, identify affected functions via CloudTrail, redeploy under new profile version

## Prompt

The profile version IVYAAABRQEXAMPLE of signing profile
"lambda-signing-prod" has been revoked. Function my-prod-function
still has CSC "lambda-csc-prod" listing that version in
AllowedPublishingProfiles. Tell me what to do, including removing
the ARN from the CSC and redeploying from a known-good signed
artifact under a new profile version.
