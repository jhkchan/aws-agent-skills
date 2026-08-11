---
name: signer-signing-profile-deployer
description: >-
  Provisions AWS Signer signing profiles with production defaults:
  platform selection (AWSLambda-SHA384-ECDSA, AmazonFreeRTOS,
  AWSIoT) where the platform fixes the cryptographic algorithm,
  Lambda code signing config (code-signing-config ARN, allowed
  publishing profiles, untrusted-artifact-on-violation=Enforce),
  signing job creation (source S3, destination S3, profile ARN),
  certificate validation, signature verification at Lambda deploy
  time, revocation tracking, profile versioning, IAM permissions,
  IoT device management integration, CloudTrail audit, and
  trusted profile management. Emits a READY_TO_DEPLOY checklist
  with verification commands. Use when creating a signing
  profile, configuring Lambda code signing, starting a signing
  job, or managing trusted profile versions. Triggers: create
  signer signing profile, Lambda code signing config, signer
  signing job, allowed publishing profiles, profile versioning.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with signer,
  lambda, iam, s3, iot, and sts access. Works with Terraform
  aws_signer_signing_profile / aws_lambda_code_signing_config /
  aws_signer_signing_job resources and CloudFormation
  AWS::Signer::SigningProfile / AWS::Lambda::CodeSigningConfig
  templates.
keywords:
  - aws
  - signer
  - code signing
  - signing profile
  - cloudops
  - deploy
  - provisioning
  - lambda code signing
  - aws-lambda-sha384-ecdsa
  - amazonfreertos
  - awsiot
  - signing job
  - code signing config
  - allowed publishing profiles
  - untrusted artifact on violation
  - certificate validation
  - signature verification
  - profile versioning
  - trusted profile
tags:
  - aws
  - signer
  - code-signing
  - signing-profile
  - cloudops
  - deploy
  - security
  - provisioning
  - lambda-code-signing
  - signing-job
  - profile-versioning
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - signer
    - code-signing
    - signing-profile
    - cloudops
    - deploy
    - security
    - provisioning
    - lambda-code-signing
    - signing-job
    - profile-versioning
  dependencies:
    - aws-orchestrator
  keywords:
    - create signer signing profile
    - aws-lambda-sha384-ecdsa
    - amazonfreertos signing
    - awsiot signing
    - lambda code signing config
    - signer signing job
    - allowed publishing profiles
    - untrusted artifact on violation
    - signer certificate validation
    - signature verification lambda
    - profile versioning
    - trusted profile management
  when_to_use: >-
    Invoke when the user wants to create an AWS Signer signing
    profile, configure Lambda code signing, start a signing job,
    validate a Signer certificate chain, manage trusted profile
    versions, or audit signing operations via CloudTrail. Do NOT
    invoke for AWS KMS asymmetric signing (use kms-key-deployer),
    ACM certificate management (use acm-certificate-deployer), or
    CloudHSM key lifecycle (use cloudhsm-cluster-deployer).
---

# Signer Signing Profile Deployer

An AWS CloudOps agent skill that provisions AWS Signer signing
profiles and Lambda code signing configurations with correct
production defaults. The skill walks platform selection (which
determines the cryptographic algorithm), profile creation, Lambda
code signing config enforcement, signing job submission, certificate
validation, signature verification, profile versioning, and
CloudTrail audit posture; captures every configuration decision;
explains why each default matters; and emits a READY_TO_DEPLOY
checklist with copy-pasteable verification commands.

## Activation keywords

create signer signing profile, AWSLambda-SHA384-ECDSA, AmazonFreeRTOS
signing, AWSIoT signing, Lambda code signing config, signer signing
job, allowed publishing profiles, untrusted artifact on violation,
profile versioning, trusted profile management.

## STRICT output contract

When this skill is invoked with a Signer-provisioning request (create
a signing profile, configure Lambda code signing, start a signing
job, validate a signer certificate, or manage profile versions), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in
"Output format" using the literal all-caps labels `SIGNER:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit the
block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear. The
response uses these literal labels: `SIGNER: <profile-name>
(<platform-id>)`, then `VERDICT:`, then `CHECKLIST:` with status
markers (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`), then
`VERIFICATION_COMMANDS:` with indented `aws signer ...` and
`aws lambda ...` commands.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Platform selection (crypto algorithm) | Core model |
| Step 2 — Profile creation and versioning | Provisioning step |
| Step 3 — Lambda CSC (enforces at UPDATE) | Lambda integration |
| Step 4 — Signing job (immutable once created) | Signing artifacts |
| Step 5 — Certificate validation | Trust chain |
| Step 6 — Signature verification at deploy | Runtime enforcement |
| Step 7 — Revocation tracking | Revocation posture |
| Step 8 — IAM permissions | Least privilege |
| Step 9 — IoT device management | IoT firmware signing |
| Step 10 — CloudTrail audit | Auditability |
| Step 11 — Trusted profile management | Lifecycle governance |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/lambda-code-signing.md | Lambda CSC deep detail |
| references/signing-jobs-and-certificates.md | Signing job + cert detail |

## Mindset

**One-line takeaway:** An AWS Signer signing profile is a named,
versioned identity that bundles a platform (which fixes the
cryptographic algorithm) with a signing certificate AWS generates
and rotates for you. Lambda code signing configs reference one or
more allowed publishing profiles and reject any deployment package
whose signature is missing, untrusted, or stale — enforcement
happens at function CREATE and UPDATE, never at runtime. A signing
job is immutable once started: the signed artifact cannot be
re-signed under the same job.

Three misconceptions dominate Signer misdesign at provisioning time:

- **"Any signing profile works for any workload."** It does not.
  Signer platforms are workload-scoped. `AWSLambda-SHA384-ECDSA` is
  the ONLY valid platform for Lambda code signing (ECDSA on P-384
  over SHA-384). `AmazonFreeRTOS` and `AWSIoT` are firmware scopes
  with their own primitives. Picking the wrong platform produces a
  profile that Lambda's verifier rejects at `UpdateFunctionCode`.

- **"Lambda code signing is enforced at runtime."** It is not.
  Lambda checks the signature ONLY when the function or layer
  version is created or updated. Once published, runtime invocation
  does not re-verify. If the trusted profile is later revoked, the
  already-published version keeps running until the operator
  redeploys — the control is a deploy gate, not a runtime gate.

- **"A signing job can be re-run or patched."** It cannot. A signing
  job, once `Succeeded`, is immutable: the signed artifact in the
  destination S3 prefix is fixed, the job ARN is fixed, and the
  profile version used is fixed. To re-sign after a profile rotation
  or cert revocation, you MUST start a new job. There is no
  `UpdateSigningJob` API.

## Configuration dependency graph (novel heuristic)

Signer configurations are NOT independent. The platform fixes the
crypto algorithm; the CSC references allowed publishing profiles by
ARN (with version); the signing job references the profile version
and produces an immutable signed artifact; signature verification at
Lambda deploy time uses the same CSC. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Signing profile | platform chosen; `signer:PutSigningProfile` | version immutable once created; Active after first successful job | profile ARN + version for CSC and jobs |
| Profile version | profile exists; platform fixes algorithm | version cannot be re-targeted; revocation invalidates jobs that used the version AFTER publish, not retroactively | stable reference for CSC and audit |
| Lambda CSC | ≥1 allowed publishing profile ARN; `untrusted-artifact-on-violation` set | `Enforce` rejects the deploy; `Warn` logs only — silent if mis-set | deploy-time gate on `UpdateFunctionCode` |
| CSC → function | CSC ARN exists; function exists | association via `UpdateFunctionConfiguration`; takes effect on NEXT deploy, not in-place | every subsequent update must pass signature check |
| Signing job | profile ARN+version; source S3 object; destination bucket with signer write grant | signed artifact is immutable; job ID fixed; cannot retry in place | signed artifact for Lambda deploy / OTA client |
| Certificate validation | profile Active; AWS-generated signer cert chain | signer rotates the cert periodically; verification MUST re-fetch each check | trust chain for offline verifiers and Lambda deploy-time check |
| Signature verification at deploy | function has CSC with the profile in `AllowedPublishingProfiles` | verification on `UpdateFunctionCode` / `PublishLayerVersion`, never on invoke; stale version = `SignatureMismatchException` | deploy gate blocking unsigned/untrusted code |
| IAM for Signer | `signer:StartSigningJob`, `signer:PutSigningProfile`; Lambda role trusts `lambda:UpdateFunctionCode` | missing `signer:StartSigningJob` on the CI role is the most common CI failure | least-privilege CI pipeline |
| CloudTrail audit | Signer is a CloudTrail-logged service in all commercial regions | `StartSigningJob` and `PutSigningProfile` appear in CloudTrail; CSC changes appear under `lambda:` events | audit trail of who signed what, when, with which profile version |

**The platform-fixes-algorithm row is the one a baseline model
misses.** A naive answer lists platforms as interchangeable. In
reality the platform string is the single source of truth for the
hash and signature algorithm — there is no separate `--algorithm`
flag. The CSC enforcement-at-UPDATE-only row is the second most
missed: operators assume runtime enforcement and are surprised when
a revoked-profile version keeps serving traffic.

**Cross-dependency gotchas:**
- A CSC references a profile ARN WITH version suffix. Promoting a
  new profile version requires updating the CSC's
  `AllowedPublishingProfiles`.
- `UntrustedArtifactOnViolation=Enforce` blocks deploys that fail
  validation; `Warn` only logs (silent if mis-set).
- A signing job is immutable. If the source S3 object changes after
  the job starts, the signed artifact in destination is NOT updated.
  Re-sign with a new job.
- Signer rotates signing certificates on its own schedule. Re-fetch
  via `GetSigningProfile` for offline verification; do not pin.

## Expert heuristic: the platform determines the cryptographic algorithm

A baseline model says "create a signing profile." The correct
heuristic recognizes that the `--platform-id` argument fixes the hash
and signature algorithm. There is no separate algorithm selector.

```text
Platform id                     Hash        Signature        Used by
──────────────────────────────  ──────────  ───────────────  ──────────────────
AWSLambda-SHA384-ECDSA          SHA-384     ECDSA (P-384)    Lambda code signing
AmazonFreeRTOS                  SHA-256     RSA-3072         FreeRTOS OTA firmware
AWSIoT                          SHA-256     RSA-3072/ECDSA   AWS IoT device firmware
```

**Key implication:** for Lambda, the ONLY valid platform is
`AWSLambda-SHA384-ECDSA`. Picking `AWSIoT` or `AmazonFreeRTOS`
produces a profile that `CreateCodeSigningConfig` accepts (the CSC is
profile-agnostic) but Lambda rejects at `UpdateFunctionCode` because
the verifier expects ECDSA/P-384 over SHA-384.

## Expert heuristic: Lambda code signing config enforces at UPDATE, not at runtime

Lambda code signing is a deploy-time gate, not a runtime gate. The
verifier runs against the deployment package only when a new function
or layer version is published.

```text
Event                            Checked?  Action on mismatch
───────────────────────────────  ────────  ─────────────────────────
CreateFunction                   YES       rejected
UpdateFunctionCode               YES       Enforce → rejected; Warn → logged
PublishLayerVersion              YES       Enforce → rejected; Warn → logged
Invoke / runtime invocation      NO        Already-published version keeps running
PublishVersion                   NO        Version pins the previously-validated pkg
```

**Key implication:** if a trusted profile is revoked AFTER a function
version is published, that version keeps running until the operator
redeploys with a CSC that no longer lists the revoked profile. Treat
code signing as a CI/CD gate, not a runtime attestation.

## Expert heuristic: a signing job is immutable once created

A signing job takes a source S3 object, a destination S3 prefix, and
a profile version. Once the job transitions to `Succeeded`, the
signed artifact at the destination is fixed.

```text
signing job lifecycle:
  InProgress → Succeeded | Failed
  Once Succeeded: destination object, job ID, and profile version
  are all immutable. Re-signing requires a NEW StartSigningJob.
```

**Key implication:** after a profile rotation or revocation, you
MUST start a new signing job against the same source with the new
profile version, then redeploy the function pointing at the new
destination object. The previous job ID is for audit only.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** and the
specific gap must be cited.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Platform chosen (`AWSLambda-SHA384-ECDSA`, `AmazonFreeRTOS`, `AWSIoT`) | Platform fixes the crypto algorithm | Confirm workload matches platform scope |
| Source S3 bucket + key (if signing job) | `StartSigningJob` requires `source.s3.bucketName` and `source.s3.key` | `aws s3api head-object --bucket <b> --key <k>` |
| Destination S3 bucket + prefix | Signer writes here; bucket must grant Signer write | `aws s3api list-objects --bucket <b> --prefix <p>` |
| Caller IAM: `signer:PutSigningProfile` | Required to create the profile | `aws iam simulate-principal-policy ...` |
| Caller IAM: `signer:StartSigningJob` (if signing job) | Required to start a job | `aws iam simulate-principal-policy ...` |
| Lambda function exists (if associating CSC) | CSC is per-function via `UpdateFunctionConfiguration` | `aws lambda get-function-configuration --function-name <f>` |
| CSC ARN known (if updating existing CSC) | CSCs are referenced by ARN | `aws lambda list-code-signing-configs` |
| `AllowedPublishingProfiles` decision | Determines which profile ARNs (with version) are trusted | Confirm profile version ARNs |
| `UntrustedArtifactOnViolation` decision | `Enforce` blocks on mismatch; `Warn` only logs | Confirm policy intent |
| CloudTrail trail present in the region | Signer events appear in CloudTrail | `aws cloudtrail describe-trails` |

## Step 1 — Platform selection (determines the crypto algorithm)

The platform id is the single source of truth for the cryptographic
algorithm. Choose by workload. There is no `--algorithm` override.

| Workload | Platform id | Hash | Signature |
|---|---|---|---|
| Lambda code signing | `AWSLambda-SHA384-ECDSA` | SHA-384 | ECDSA on P-384 |
| FreeRTOS OTA firmware | `AmazonFreeRTOS` | SHA-256 | RSA-3072 |
| AWS IoT device firmware | `AWSIoT` | SHA-256 | RSA-3072 or ECDSA |

**Lambda constraint:** Lambda CSCs REQUIRE a profile on the
`AWSLambda-SHA384-ECDSA` platform. Any other platform in
`AllowedPublishingProfiles` fails Lambda's deploy-time verification
with `SignatureMismatchException`.

## Step 2 — Profile creation and versioning

A signing profile is named, scoped to a platform, and acquires a
version the first time you start a successful signing job against
it. The profile ARN with version suffix is what CSCs and audit
records reference.

```bash
# Create the signing profile (platform fixes the algorithm)
aws signer put-signing-profile \
  --profile-name lambda-signing-prod \
  --platform-id AWSLambda-SHA384-ECDSA --region us-east-1

# Verify the profile exists and is Active
aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query '{Status:status, Platform:platformId, Arn:arn, Version:profileVersion}' \
  --output table --region us-east-1
```

**Versioning notes:**
- Profile starts in `Active` status after `PutSigningProfile`.
- The `profileVersion` appears in the ARN's last path segment after
  a successful signing job.
- Promoting a new version: call `PutSigningProfile` with the same
  name — Signer creates a new version and points the name at it.
- Revoking a version: see Step 7.

## Step 3 — Lambda code signing config (enforces at UPDATE)

The code signing config (CSC) is the deploy-time gate. It lists the
allowed publishing profile ARNs and what to do on a violation.

```bash
# Create the code signing config (CSC)
CSC_ARN=$(aws lambda create-code-signing-config \
  --code-signing-config-name lambda-csc-prod \
  --allowed-publishers AllowedPublishingProfiles=arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod \
  --code-signing-policies UntrustedArtifactOnViolation=Enforce \
  --description "Production Lambda CSC — Enforce on violation" \
  --query 'CodeSigningConfig.CodeSigningConfigArn' --output text)

# Associate CSC with the function (takes effect on next UpdateFunctionCode)
aws lambda update-function-configuration \
  --function-name my-prod-function \
  --code-signing-config-arn-arn "$CSC_ARN" --region us-east-1

# This is where signature verification runs
aws lambda update-function-code \
  --function-name my-prod-function \
  --s3-bucket my-signed-artifacts \
  --s3-key lambda/my-prod-function.zip \
  --s3-object-version <version-id> --region us-east-1
# Expect: success if signed by a profile in AllowedPublishingProfiles
# Expect: ResourceConflictException if Enforce and signature fails
```

**Critical decisions:**
- `UntrustedArtifactOnViolation`:
  - `Enforce` — Lambda rejects the deploy with
    `ResourceConflictException` if signature is missing, untrusted,
    or signed by a revoked profile. Production default.
  - `Warn` — Lambda logs the violation but allows the deploy. Useful
    for brownfield migrations; not a control.
- `AllowedPublishingProfiles` MUST include the profile ARN WITH
  version suffix. A versionless ARN matches only the default version.

## Step 4 — Signing job creation (immutable once created)

A signing job signs a source S3 object with a profile version and
writes the signed artifact to a destination S3 prefix. The signed
artifact is immutable; the job ID is fixed.

```bash
# Start a signing job
JOB_ID=$(aws signer start-signing-job \
  --source 'source={s3={bucketName=my-unsigned-artifacts,key=lambda/my-prod-function.zip,version=<version-id>}}' \
  --destination 'destination={s3={bucket=my-signed-artifacts,prefix=lambda/signed/}}' \
  --profile-name lambda-signing-prod \
  --query 'jobId' --output text --region us-east-1)

# Poll for completion (signing is asynchronous)
aws signer describe-signing-job --job-id "$JOB_ID" \
  --query '{Status:status, Source:source, Destination:destination, Profile:profileName, CompletedAt:completedAt}' \
  --output table --region us-east-1
# Expected status: Succeeded
```

**Immutability constraints:**
- Once `status == Succeeded`, the destination object is fixed. There
  is no `UpdateSigningJob` API.
- Re-signing after a profile rotation or revocation requires a new
  `StartSigningJob` call.
- The job ID is what CloudTrail records and what downstream verifiers
  use for provenance.

**Common mistake:** pointing `UpdateFunctionCode` at the unsigned
source object after the job completes. The function must point at the
SIGNED artifact in the destination prefix.

## Step 5 — Certificate validation via Signer

Signer generates and rotates the signing certificate for each
profile. For offline verifiers and audit, fetch the certificate
chain.

```bash
# Retrieve the signing certificate for the profile
aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query 'signingMaterial.{CertificateArn:certificateArn}' \
  --output table --region us-east-1

# For a specific signing job, the certificate used is in describe-signing-job
aws signer describe-signing-job --job-id "$JOB_ID" \
  --query '{Signature:signature, SignedObject:signedObject, ProfileVersion:profileVersion}' \
  --output table --region us-east-1
```

**Key implication:** Signer rotates certificates on its own schedule.
Always re-fetch the active certificate via `GetSigningProfile`; do
not pin a cached certificate indefinitely.

## Step 6 — Signature verification at Lambda deploy time

Lambda verifies the signature of a deployment package when
`UpdateFunctionCode` or `PublishLayerVersion` runs against a
function or layer that has a CSC association. The check:

1. Extract the signature block from the package.
2. Resolve the profile version that produced the signature.
3. Verify the profile version is in the CSC's
   `AllowedPublishingProfiles`.
4. If revoked → block (Enforce) or log (Warn).
5. Verify the signature using the profile's active certificate.

```bash
# Update function code — this is where signature verification runs
aws lambda update-function-code \
  --function-name my-prod-function \
  --zip-file fileb://./signed-package.zip --region us-east-1

# Confirm the function's CSC association
aws lambda get-function-configuration \
  --function-name my-prod-function \
  --query 'CodeSigningConfigArn' --region us-east-1
```

**Critical:** runtime invocation does NOT re-verify. A previously
published version keeps running even if the profile that signed it
is later revoked.

## Step 7 — Revocation tracking

Revocation invalidates a profile version. New deploys referencing a
revoked version fail (Enforce) or log (Warn). Already-published
function versions are NOT auto-rolled-back.

```bash
# Inspect profile status and revocation state
aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query '{Status:status, RevocationInfo:revocationParameters}' \
  --output table --region us-east-1

# Audit CloudTrail for revocation events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CancelSigningProfile \
  --max-results 10 --region us-east-1
```

**Operational rule:** when a profile is revoked, immediately (a)
remove its ARN from any CSC's `AllowedPublishingProfiles`, (b)
identify functions whose last deploy used that version (via
CloudTrail), and (c) redeploy from a known-good signed artifact
under a new profile version.

## Step 8 — IAM permissions for Signer

Least-privilege IAM for a CI pipeline that signs and deploys Lambda
code. Minimum action set:

- **Signer:** `signer:PutSigningProfile`,
  `signer:GetSigningProfile`, `signer:ListSigningProfiles`,
  `signer:StartSigningJob`, `signer:DescribeSigningJob`,
  `signer:ListSigningJobs`.
- **Lambda:** `lambda:CreateCodeSigningConfig`,
  `lambda:UpdateCodeSigningConfig`, `lambda:GetCodeSigningConfig`,
  `lambda:ListCodeSigningConfigs`,
  `lambda:UpdateFunctionConfiguration`,
  `lambda:UpdateFunctionCode`, `lambda:GetFunctionConfiguration`.
- **S3:** `s3:GetObject` on the unsigned source; `s3:PutObject` on
  the signed destination.

**Common pitfall:** granting `signer:*` instead of the call sites
above. Use resource ARNs to narrow further in multi-tenant CI.

## Step 9 — IoT device management integration

For IoT firmware signing (`AWSIoT`, `AmazonFreeRTOS`), the signed
artifact is consumed by OTA (over-the-air) update jobs and by the
device's code-signing verification extension.

```text
1. Signer signs the firmware image → signed artifact in S3.
2. IoT OTA job references the signed artifact (S3 URL or stream).
3. Device receives the image, verifies against a pinned Signer root
   certificate (provisioned at manufacturing).
4. Device applies the update or rejects on signature failure.
```

```bash
# Create an IoT-signing profile (NOT valid for Lambda CSC)
aws signer put-signing-profile \
  --profile-name iot-firmware-prod \
  --platform-id AWSIoT --region us-east-1

# Start a signing job for the firmware image
aws signer start-signing-job \
  --source 'source={s3={bucketName=my-unsigned-firmware,key=firmware-v1.bin}}' \
  --destination 'destination={s3={bucket=my-signed-firmware,prefix=firmware/signed/}}' \
  --profile-name iot-firmware-prod \
  --query 'jobId' --output text --region us-east-1
```

**Constraint:** IoT and FreeRTOS profiles CANNOT be referenced by a
Lambda CSC. They produce signatures in a format Lambda's verifier
does not understand.

## Step 10 — CloudTrail audit of signing operations

Signer is a CloudTrail-logged service. The key events:

| Event name | When | Recorded fields |
|---|---|---|
| `PutSigningProfile` | Profile created or version promoted | profileName, platformId, profileVersion |
| `StartSigningJob` | Job submitted | jobId, profileName, source S3, destination S3 |
| `GetSigningProfile` | Profile retrieved | profileName |
| `CancelSigningProfile` | Profile revoked | profileName, profileVersion |
| `TagResource` / `UntagResource` | Tags changed | profileArn |

```bash
# Audit signing operations over the last 24 hours
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=signer.amazonaws.com \
  --start-time $(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 50 --region us-east-1

# Audit CSC changes (Lambda service events)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateCodeSigningConfig \
  --max-results 20 --region us-east-1
```

## Step 11 — Trusted profile management

Treat signing profiles as a trust graph, not just configuration:

- Maintain an allow-list of profile ARNs (with versions) that are
  permitted in each CSC. ARNs outside the allow-list must not be in
  `AllowedPublishingProfiles`.
- Use Signer tags to classify profiles (`Environment=prod`,
  `Workload=lambda`, `Owner=platform-team`).
- Rotate profiles on a fixed cadence (e.g., annually): promote a new
  version, update the CSC, re-sign artifacts, verify, then retire
  the old version.
- Revoke immediately on compromise.

```bash
# Tag a signing profile for governance
aws signer tag-resource \
  --resource-arn arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod \
  --tags Environment=prod,Workload=lambda,Owner=platform-team \
  --region us-east-1

# List all profiles with status and platform
aws signer list-signing-profiles \
  --query 'profiles[*].{Name:profileName,Platform:platformId,Status:status,Arn:arn}' \
  --output table --region us-east-1
```

## Recent features

- **Signer profile permission resource (2023-2024):**
  `AWS::Signer::ProfilePermission` and the Terraform
  `aws_signer_signing_profile_permission` resource allow declarative
  cross-account profile sharing (previously CLI-only).
- **Lambda CSC enhancements (2023-2024):** CSC supports multiple
  `AllowedPublishingProfiles` and per-profile version pinning,
  enabling canary rollouts of new profile versions.
- **CloudTrail coverage expansion (2023-2024):** read events
  (`GetSigningProfile`, `DescribeSigningJob`) now logged in all
  commercial regions.
- **Tag-based access control (2024-2025):** `aws:ResourceTag`
  conditions honored on `signer:StartSigningJob` and
  `signer:PutSigningProfile`, enabling ABAC for multi-tenant CI.
- **Cross-region signing (2024-2025):** Signer in more regions;
  profiles shareable cross-region. IoT (2024-2025) consumes
  Signer-produced signatures directly in OTA job documents.

## NEVER do these things

1. **NEVER use a non-`AWSLambda-SHA384-ECDSA` profile in a Lambda
   CSC.** Lambda's verifier expects ECDSA on P-384 over SHA-384.
   Other platforms are rejected at `UpdateFunctionCode`.

2. **NEVER assume Lambda code signing is enforced at runtime.**
   Verification runs ONLY on `UpdateFunctionCode` and
   `PublishLayerVersion`. Once a version is published, invocation
   does NOT re-verify.

3. **NEVER treat a signing job as mutable.** A job, once Succeeded,
   is immutable. Re-signing requires a new `StartSigningJob`. There
   is no `UpdateSigningJob` API.

4. **NEVER set `UntrustedArtifactOnViolation=Warn` in production
   without an exception.** Warn only logs; Enforce is the production
   default.

5. **NEVER pin a cached Signer certificate indefinitely.** Signer
   rotates signing certificates on its own schedule. Re-fetch via
   `GetSigningProfile`.

6. **NEVER leave a revoked profile version in
   `AllowedPublishingProfiles`.** A revoked version blocks new
   deploys but does NOT roll back already-published versions. Remove
   the ARN on revoke and redeploy.

7. **NEVER assume `signer:*` is the right IAM scope for CI.** Use
   the minimum set (`PutSigningProfile`, `GetSigningProfile`,
   `StartSigningJob`, `DescribeSigningJob`) and narrow by ARN.

8. **NEVER confuse Signer with KMS asymmetric signing.** Signer is
   a managed code-signing service with AWS-generated certificates
   and platform-scoped algorithms. KMS asymmetric keys give you
   BYO key material but no Lambda CSC integration.

9. **NEVER point `UpdateFunctionCode` at the unsigned source object
   after a signing job completes.** Lambda expects the SIGNED
   artifact in the destination S3 prefix.

10. **NEVER skip the CloudTrail audit setup.** Signer events
    (`PutSigningProfile`, `StartSigningJob`, `CancelSigningProfile`)
    are the provenance record for every signed artifact.

## Output format

```text
SIGNER: <profile-name> (<platform-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Profile name: <name>
  [✓|✗] Platform: <AWSLambda-SHA384-ECDSA | AmazonFreeRTOS | AWSIoT> (fixes hash + signature)
  [✓|✗] Profile status: Active | Pending | Canceled
  [✓|✗] Profile version: <version-id>
  [✓|✗] Profile ARN: arn:aws:signer:<region>:<acct>:/signing-profiles/<name>
  [✓|✗] Lambda code signing config: <csc-name> (<csc-arn>)
  [✓|✗] AllowedPublishingProfiles: <profile-arn-list>
  [✓|✗] UntrustedArtifactOnViolation: Enforce | Warn
  [✓|✗] CSC → function association: <function-name>
  [✓|✗] Signing job: <job-id> (status: Succeeded | InProgress | Failed)
  [✓|✗] Signing job source: s3://<bucket>/<key>
  [✓|✗] Signing job destination: s3://<bucket>/<prefix>
  [✓|✗] Certificate validation: Signer-managed cert chain (re-fetch on each verify)
  [✓|✗] Signature verification at deploy: UpdateFunctionCode gates on signature (Enforce)
  [✓|✗] Revocation tracking: <profile-version-revocation-status>
  [✓|✗] IAM: signer:PutSigningProfile, signer:StartSigningJob (caller)
  [✓|✗] CloudTrail audit: trail present in <region>; signer events logged
  [✓|✗] Trusted profile governance: tags applied, allow-list current
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws signer get-signing-profile --profile-name <name> --region <region>
  aws lambda get-code-signing-config --code-signing-config-arn <csc-arn> --region <region>
  aws lambda get-function-configuration --function-name <name> --region <region>
  aws signer describe-signing-job --job-id <job-id> --region <region>
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=signer.amazonaws.com --region <region>
```

### Worked example — Lambda signing profile with CSC and deploy-time enforcement

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

## Error handling

### CreateCodeSigningConfig fails with ValidationException
- The `AllowedPublishingProfiles` ARN is malformed or the profile is
  on the wrong platform. Confirm ARN includes the version suffix and
  platform is `AWSLambda-SHA384-ECDSA`.

### UpdateFunctionCode fails with ResourceConflictException
- Signature verification failed. Package was not signed by a profile
  in `AllowedPublishingProfiles`, the version is revoked, or
  `Enforce` is correctly blocking an unsigned package. Re-sign and
  redeploy.

### StartSigningJob fails with AccessDeniedException
- Caller missing `signer:StartSigningJob` on the profile ARN or
  `s3:GetObject` on the source bucket.

### Signing job stuck InProgress
- Poll with `describe-signing-job`. If stuck >15 min, source may be
  inaccessible or destination bucket missing Signer write grant.

### Profile version not appearing in ARN
- Version suffix is assigned after the first successful signing job.

### Already-published function keeps running after profile revoke
- Expected. Code signing is a deploy-time gate. Revoke triggers a
  CI/CD redeploy workflow, not a runtime rollback.

## Domain

AWS CloudOps / AWS Signer Signing Profile Provisioning & Lambda Code Signing Config.

## AWS documentation

- **AWS Signer developer guide** — https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html
- **Signing profiles** — https://docs.aws.amazon.com/signer/latest/developerguide/signing-profiles.html
- **Signing jobs** — https://docs.aws.amazon.com/signer/latest/developerguide/signing-jobs.html
- **Lambda code signing** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html
- **CreateCodeSigningConfig API** — https://docs.aws.amazon.com/lambda/latest/api/API_CreateCodeSigningConfig.html
- **Signer IAM** — https://docs.aws.amazon.com/signer/latest/developerguide/auth-and-access-control.html
- **Signer CloudTrail** — https://docs.aws.amazon.com/signer/latest/developerguide/logging-using-cloudtrail.html
- **IoT code signing** — https://docs.aws.amazon.com/iot/latest/developerguide/code-signing.html
