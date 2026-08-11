---
description: Provision an AWS Signer signing profile with production-grade defaults (platform selection — AWSLambda-SHA384-ECDSA, AmazonFreeRTOS, AWSIoT — where the platform fixes the cryptographic algorithm, Lambda code signing config with AllowedPublishingProfiles and Enforce on violation, signing job against S3 source/destination, certificate validation, profile versioning, IAM permissions, CloudTrail audit). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create signer signing profile"
  - "deploy signer signing profile"
  - "aws signer"
  - "code signing profile"
  - "lambda code signing config"
  - "code signing config arn"
  - "allowed publishing profiles"
  - "untrusted artifact on violation"
  - "signer signing job"
  - "start signing job"
  - "signer certificate"
  - "signing profile version"
  - "trusted profile"
  - "awslambda-sha384-ecdsa"
  - "amazonfreertos signing"
  - "awsiot signing"
routes_to: signer-signing-profile-deployer
---

# /aws:deploy-signer-signing-profile

Activate the `signer-signing-profile-deployer` skill and provision
an AWS Signer signing profile with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Platform selection (determines the crypto algorithm; no
   `--algorithm` override)
2. Profile creation and versioning
3. Lambda code signing config (enforces at UPDATE, not runtime)
4. Signing job creation (immutable once Succeeded)
5. Certificate validation via Signer (re-fetch on each verify)
6. Signature verification at Lambda deploy time
7. Revocation tracking
8. IAM permissions for Signer
9. IoT device management integration (AWSIoT, AmazonFreeRTOS)
10. CloudTrail audit of signing operations
11. Trusted profile management

## When to use

- You need to create a Signer signing profile.
- You are configuring Lambda code signing (CSC).
- You are starting a signing job against an S3 source object.
- You need to validate a Signer certificate chain.
- You are promoting or revoking a profile version.
- You need to audit signing operations via CloudTrail.
- You are signing IoT / FreeRTOS firmware for OTA.

## When NOT to use

- **AWS KMS asymmetric signing** — use `kms-key-deployer`. KMS gives
  BYO key material and free-form algorithm but no Lambda CSC
  integration.
- **ACM certificate management** — use `acm-certificate-deployer`.
- **CloudHSM key lifecycle** — use `cloudhsm-cluster-deployer`.
- **Auditing existing signing profiles** — use Signer audit skills.

## How to invoke

### Slash command

```
/aws:deploy-signer-signing-profile
```

Then provide: profile name, platform id
(`AWSLambda-SHA384-ECDSA`, `AmazonFreeRTOS`, or `AWSIoT`),
allowed publishing profile ARNs (with version),
`UntrustedArtifactOnViolation` decision, function name (if CSC
association), source S3 bucket/key, destination S3 bucket/prefix,
tags.

### Natural language

Any of these routes to the same skill:

- "create a signer signing profile on AWSLambda-SHA384-ECDSA"
- "configure Lambda code signing config with Enforce"
- "start a signing job for my Lambda package"
- "create an AWSIoT firmware signing profile"
- "what happens when I revoke a signer profile version?"

### CLI routing

```bash
node cli/bin/cli.js route "create a signer signing profile"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create Signer resources. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-signer-signing-profile

     Create a Signer signing profile "lambda-signing-prod" on
     AWSLambda-SHA384-ECDSA. Create CSC "lambda-csc-prod" with
     Enforce, associated with my-prod-function. Source bucket
     my-unsigned-artifacts, destination my-signed-artifacts.

Skill:
  SIGNER: lambda-signing-prod (AWSLambda-SHA384-ECDSA)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Platform: AWSLambda-SHA384-ECDSA (SHA-384, ECDSA P-384)
    [✓] Lambda CSC: lambda-csc-prod
    [✓] AllowedPublishingProfiles: versioned ARN
    [✓] UntrustedArtifactOnViolation: Enforce
    [✓] Signing job: Succeeded (immutable)
  VERIFICATION_COMMANDS:
    aws signer get-signing-profile --profile-name lambda-signing-prod --region us-east-1
    aws lambda get-code-signing-config --code-signing-config-arn <csc-arn> --region us-east-1
```

## References

- Skill definition: `skills/signer-signing-profile-deployer/SKILL.md`
- Lambda code signing guide: `skills/signer-signing-profile-deployer/references/lambda-code-signing.md`
- Signing jobs + certificates guide: `skills/signer-signing-profile-deployer/references/signing-jobs-and-certificates.md`
- Eval suite: `skills/signer-signing-profile-deployer/evals/evals.json`
