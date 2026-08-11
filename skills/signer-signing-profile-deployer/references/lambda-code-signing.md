# Lambda Code Signing — Signer Signing Profile Deployer

Deep reference on Lambda code signing configuration (CSC) mechanics:
how the CSC interacts with `UpdateFunctionCode` and
`PublishLayerVersion`, what `UntrustedArtifactOnViolation` actually
enforces, how `AllowedPublishingProfiles` is matched at deploy time,
how profile version pinning works, and how to migrate a brownfield
function fleet to a CSC. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## CSC data model

A code signing config is a regional Lambda resource identified by an
ARN of the form:

```text
arn:aws:lambda:<region>:<acct>:code-signing-config:<csc-id>
```

It carries:

- `AllowedPublishingProfiles` — list of Signer profile ARNs (with
  version suffix) trusted to sign function/layer packages.
- `UntrustedArtifactOnViolation` — `Enforce` (default for prod) or
  `Warn`.
- `Description` — free text.

A CSC is associated with a function via
`UpdateFunctionConfiguration --code-signing-config-arn-arn <csc-arn>`.
The association is per-function. A single CSC can be associated with
many functions in the same account+region.

## Enforcement lifecycle

```text
Event                          Signature checked?  Action on mismatch
─────────────────────────────  ──────────────────  ─────────────────────────
CreateFunction                 YES (if CSC set)    rejected (Enforce) / logged (Warn)
UpdateFunctionCode             YES                 rejected (Enforce) / logged (Warn)
PublishLayerVersion            YES                 rejected (Enforce) / logged (Warn)
Invoke                         NO                  already-published version keeps running
PublishVersion                 NO                  pins previously-validated package
UpdateFunctionConfiguration    NO                  does not touch code
```

**Key implication:** revoking a profile version AFTER a function
version is published does NOT roll back that version. The version
keeps serving traffic until the operator redeploys. Treat code
signing as a deploy gate, not a runtime attestation.

## AllowedPublishingProfiles — version semantics

The ARN you put in `AllowedPublishingProfiles` MUST include the
profile version suffix, e.g.

```text
arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod/IVYAAABRQEXAMPLE
```

Without the suffix, the CSC matches the profile's default version
(whatever `profileVersion` the `GetSigningProfile` call returns at
the time of the deploy). This is brittle: a profile rotation that
promotes a new version silently changes which version the CSC trusts.

**Recommendation:** pin the version explicitly. To promote a new
version, update the CSC's `AllowedPublishingProfiles` to include the
new ARN, then remove the old ARN after the new version is verified.

## Enforce vs Warn

- `Enforce` — Lambda rejects the deploy with
  `ResourceConflictException`. The function code is NOT updated.
  This is the production default.
- `Warn` — Lambda accepts the deploy and logs the violation to
  CloudWatch under the Lambda log group. The function code IS
  updated. Useful for brownfield migrations; not a security control.

**Brownfield migration pattern:**
1. Set the CSC to `Warn`.
2. Deploy all functions through the signed-artifact pipeline.
3. Watch CloudWatch for any `Warn` entries.
4. Fix signing pipeline gaps until no `Warn` entries appear.
5. Flip the CSC to `Enforce`.

## Migrating a function fleet to a CSC

```bash
# 1. Create the CSC (Warn initially)
CSC_ARN=$(aws lambda create-code-signing-config \
  --code-signing-config-name lambda-csc-prod \
  --allowed-publishers AllowedPublishingProfiles=arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod/IVYAAABRQEXAMPLE \
  --code-signing-policies UntrustedArtifactOnViolation=Warn \
  --query 'CodeSigningConfig.CodeSigningConfigArn' --output text)

# 2. Discover functions to migrate
FUNCTIONS=$(aws lambda list-functions \
  --query 'Functions[*].FunctionName' --output text --region us-east-1)

# 3. Associate the CSC with each function
for FN in $FUNCTIONS; do
  aws lambda update-function-configuration \
    --function-name "$FN" \
    --code-signing-config-arn-arn "$CSC_ARN" --region us-east-1
done

# 4. Sign all deployment packages and redeploy
# 5. After verification, flip to Enforce
aws lambda update-code-signing-config \
  --code-signing-config-arn "$CSC_ARN" \
  --code-signing-policies UntrustedArtifactOnViolation=Enforce \
  --region us-east-1
```

## Terraform example

```hcl
# Signing profile (platform fixes the algorithm)
resource "aws_signer_signing_profile" "lambda" {
  name       = "lambda-signing-prod"
  platform_id = "AWSLambda-SHA384-ECDSA"

  tags = {
    Environment = "production"
    Workload    = "lambda"
  }
}

# Code signing config (CSC)
resource "aws_lambda_code_signing_config" "csc" {
  code_signing_config_name = "lambda-csc-prod"
  description              = "Production Lambda CSC"

  allowed_publishers {
    allowed_publishing_profiles = [aws_signer_signing_profile.lambda.arn]
  }

  policies {
    untrusted_artifact_on_violation = "Enforce"
  }
}

# Associate CSC with each function
resource "aws_lambda_function" "signed" {
  function_name            = "my-prod-function"
  code_signing_config_arn  = aws_lambda_code_signing_config.csc.arn
  # ... other required fields ...
}
```

## Common pitfalls

1. **Versionless ARN in `AllowedPublishingProfiles`.** Promoting a
   new profile version silently changes which version the CSC
   trusts. Pin the version.

2. **`Warn` left in production.** `Warn` only logs; it does not
   block. Flip to `Enforce` after migration.

3. **Wrong-platform profile.** Only `AWSLambda-SHA384-ECDSA`
   produces a signature that Lambda's verifier accepts.

4. **Expecting runtime enforcement.** Once published, a version
   keeps running even if the signing profile is revoked. Revoke
   triggers a redeploy workflow, not a runtime rollback.

5. **Forgetting the associate step.** Creating the CSC does not
   associate it with any function. You must call
   `UpdateFunctionConfiguration --code-signing-config-arn-arn` per
   function.

6. **Caching the Signer certificate.** Signer rotates signing
   certificates on its own schedule. Always re-fetch via
   `GetSigningProfile` for offline verification.
