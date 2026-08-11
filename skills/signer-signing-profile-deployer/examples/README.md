# End-to-End Example: AWS Signer Signing Profile Deployment

A walkthrough showing how to use the
`signer-signing-profile-deployer` skill from invocation through
verification. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

You are provisioning an `AWSLambda-SHA384-ECDSA` signing profile,
attaching a Lambda code signing config (CSC) that enforces on
violation, and starting a signing job for the function's deployment
package. The signing needs:

- Profile name: `lambda-signing-prod` (platform
  `AWSLambda-SHA384-ECDSA`)
- Account: `111122223333`, region `us-east-1`
- CSC: `lambda-csc-prod` with
  `UntrustedArtifactOnViolation=Enforce`
- Function: `my-prod-function`
- Source: `s3://my-unsigned-artifacts/lambda/my-prod-function.zip`
- Destination: `s3://my-signed-artifacts/lambda/signed/`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-signer-signing-profile
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Signer signing profile lambda-signing-prod on
      AWSLambda-SHA384-ECDSA. Attach a Lambda CSC named
      lambda-csc-prod with Enforce, associated with
      my-prod-function. Source my-unsigned-artifacts, destination
      my-signed-artifacts prefix lambda/signed/."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a signer signing profile"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SIGNER: lambda-signing-prod (AWSLambda-SHA384-ECDSA)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Profile name: lambda-signing-prod
  [✓] Platform: AWSLambda-SHA384-ECDSA (SHA-384, ECDSA on P-384)
  [✓] Profile status: Active
  [✓] Profile version: IVYAAABRQEXAMPLE
  [✓] Profile ARN: arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod
  [✓] Lambda CSC: lambda-csc-prod (arn:aws:lambda:us-east-1:111122223333:code-signing-config:csc-aaa111222)
  [✓] AllowedPublishingProfiles: arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod/IVYAAABRQEXAMPLE
  [✓] UntrustedArtifactOnViolation: Enforce
  [✓] CSC → function association: my-prod-function
  [✓] Signing job: 7c0e1234-abcd-1a2b-3c4d-5e6f7a8b9c0d (status: Succeeded)
  [✓] Signing job source: s3://my-unsigned-artifacts/lambda/my-prod-function.zip
  [✓] Signing job destination: s3://my-signed-artifacts/lambda/signed/
  [✓] Certificate validation: Signer-managed cert chain (re-fetched via GetSigningProfile)
  [✓] Signature verification at deploy: Enforce
  [✓] Revocation tracking: no active revocations
  [✓] IAM: signer:PutSigningProfile, signer:StartSigningJob (caller)
  [✓] CloudTrail audit: trail present in us-east-1; signer events logged
  [✓] Trusted profile governance: tags applied, allow-list current
  [✓] Tags: Environment=production, Workload=lambda, Owner=platform-team
VERIFICATION_COMMANDS:
  aws signer get-signing-profile --profile-name lambda-signing-prod --region us-east-1
  aws lambda get-code-signing-config --code-signing-config-arn arn:aws:lambda:us-east-1:111122223333:code-signing-config:csc-aaa111222 --region us-east-1
  aws lambda get-function-configuration --function-name my-prod-function --region us-east-1
  aws signer describe-signing-job --job-id 7c0e1234-abcd-1a2b-3c4d-5e6f7a8b9c0d --region us-east-1
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=signer.amazonaws.com --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the signing profile (platform fixes the algorithm)
aws signer put-signing-profile \
  --profile-name lambda-signing-prod \
  --platform-id AWSLambda-SHA384-ECDSA --region us-east-1

# Step 2: Start a signing job to materialize the profile version
JOB_ID=$(aws signer start-signing-job \
  --source 'source={s3={bucketName=my-unsigned-artifacts,key=lambda/my-prod-function.zip,version=<version-id>}}' \
  --destination 'destination={s3={bucket=my-signed-artifacts,prefix=lambda/signed/}}' \
  --profile-name lambda-signing-prod \
  --query 'jobId' --output text --region us-east-1)

# Step 3: Fetch the profile version (now that a job has succeeded)
PROFILE_VERSION=$(aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query 'profileVersion' --output text --region us-east-1)

# Step 4: Create the CSC with the versioned ARN
CSC_ARN=$(aws lambda create-code-signing-config \
  --code-signing-config-name lambda-csc-prod \
  --allowed-publishers AllowedPublishingProfiles=arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod/$PROFILE_VERSION \
  --code-signing-policies UntrustedArtifactOnViolation=Enforce \
  --query 'CodeSigningConfig.CodeSigningConfigArn' --output text --region us-east-1)

# Step 5: Associate the CSC with the function (takes effect on next deploy)
aws lambda update-function-configuration \
  --function-name my-prod-function \
  --code-signing-config-arn-arn "$CSC_ARN" --region us-east-1

# Step 6: Update function code — this is where signature verification runs
aws lambda update-function-code \
  --function-name my-prod-function \
  --s3-bucket my-signed-artifacts \
  --s3-key lambda/signed/my-prod-function.zip \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Profile status and version
aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query '{Status:status, Platform:platformId, Version:profileVersion}' \
  --output table --region us-east-1

# CSC configuration
aws lambda get-code-signing-config \
  --code-signing-config-arn "$CSC_ARN" \
  --query 'CodeSigningConfig.{Allowed:AllowedPublishers, Policy:CodeSigningPolicies}' \
  --output table --region us-east-1

# Function's CSC association
aws lambda get-function-configuration \
  --function-name my-prod-function \
  --query 'CodeSigningConfigArn' --region us-east-1

# Signing job status
aws signer describe-signing-job \
  --job-id "$JOB_ID" \
  --query '{Status:status, Source:source, Destination:destination}' \
  --output table --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Platform | Picks any platform | `AWSLambda-SHA384-ECDSA` for Lambda | Platform fixes the algorithm; only this platform satisfies Lambda's verifier |
| `AllowedPublishingProfiles` | Versionless ARN | ARN with version suffix | Versionless matches default version silently; pinning prevents surprises on rotation |
| Enforcement scope | Assumes runtime check | Deploy-time gate (`UpdateFunctionCode`) | Runtime invocation does NOT re-verify; revoke needs redeploy, not auto-rollback |
| `UntrustedArtifactOnViolation` | Defaults to Warn | `Enforce` for production | Warn only logs; Enforce actually blocks unsigned deploys |
| Signing job | Treats as re-runnable | Immutable once Succeeded | There is no `UpdateSigningJob` API; re-sign with a new job |
| Source vs destination | Points Lambda at source | Points Lambda at SIGNED destination | Lambda expects the artifact Signer wrote to the destination prefix |

---

## Related artifacts

- **Skill definition:** `skills/signer-signing-profile-deployer/SKILL.md`
- **Lambda code signing guide:** `skills/signer-signing-profile-deployer/references/lambda-code-signing.md`
- **Signing jobs + certificates guide:** `skills/signer-signing-profile-deployer/references/signing-jobs-and-certificates.md`
- **Slash command:** `commands/aws/deploy-signer-signing-profile.md`
- **Eval suite:** `skills/signer-signing-profile-deployer/evals/evals.json`
- **Legacy test cases:** `skills/signer-signing-profile-deployer/eval/test-cases.yaml`
