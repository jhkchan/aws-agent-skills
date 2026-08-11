# Eval: lambda-sha384-ecdsa-profile-with-csc

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Lambda SHA384-ECDSA profile, CSC with AllowedPublishingProfiles (version suffix), UntrustedArtifactOnViolation=Enforce, function association, signing job

## Prompt

Create a Signer signing profile "lambda-signing-prod" on the
AWSLambda-SHA384-ECDSA platform in us-east-1, account 111122223333.
Create a Lambda code signing config "lambda-csc-prod" that allows
publishing from that profile, sets UntrustedArtifactOnViolation to
Enforce, and is associated with function my-prod-function. Source
bucket my-unsigned-artifacts, destination bucket my-signed-artifacts
with prefix lambda/signed/. Tags: Environment=production,
Workload=lambda, Owner=platform-team.
