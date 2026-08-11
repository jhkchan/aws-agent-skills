# Signing Jobs and Certificates — Signer Signing Profile Deployer

Deep reference on signing jobs (lifecycle, immutability, source/
destination S3 grants), the AWS-generated signing certificate chain
(rotation, retrieval, offline verification), revocation tracking,
and CloudTrail audit. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## Signing job lifecycle

```text
signing job lifecycle:
  InProgress → Succeeded | Failed
  Once Succeeded: destination object, job ID, and profile version
  are all immutable. Re-signing requires a NEW StartSigningJob.
```

| State | Meaning | Recorded in CloudTrail |
|---|---|---|
| InProgress | Signer is processing the source object | yes (`StartSigningJob`) |
| Succeeded | Signed artifact written to destination | yes (status update) |
| Failed | Signing failed (source inaccessible, IAM grant missing, profile inactive) | yes |

**Immutability:** there is no `UpdateSigningJob` API. The signed
artifact at the destination is fixed. To re-sign after a profile
rotation, certificate revocation, or source change, you MUST call
`StartSigningJob` again with a new job ID.

## Source and destination S3 grants

The caller of `StartSigningJob` needs:

- `s3:GetObject` on the source object.
- `s3:PutObject` on the destination prefix.
- `signer:StartSigningJob` on the profile ARN.

In addition, the destination bucket must grant AWS Signer write
access via a bucket policy. Example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "signer.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-signed-artifacts/lambda/signed/*"
    }
  ]
}
```

Without this grant, the job transitions to `Failed`.

## Starting a signing job

```bash
JOB_ID=$(aws signer start-signing-job \
  --source 'source={s3={bucketName=my-unsigned-artifacts,key=lambda/my-prod-function.zip,version=<version-id>}}' \
  --destination 'destination={s3={bucket=my-signed-artifacts,prefix=lambda/signed/}}' \
  --profile-name lambda-signing-prod \
  --query 'jobId' --output text --region us-east-1)

# Poll for completion
aws signer describe-signing-job \
  --job-id "$JOB_ID" \
  --query '{Status:status, Source:source, Destination:destination, Profile:profileName, ProfileVersion:profileVersion, CompletedAt:completedAt}' \
  --output table --region us-east-1
```

The destination object key is constructed by Signer and surfaced in
`describe-signing-job`. The function's `UpdateFunctionCode` call
must reference that destination object, not the unsigned source.

## AWS-generated signing certificate

Each profile has a signing certificate that AWS Signer generates and
rotates. The certificate chain is retrievable via
`GetSigningProfile`:

```bash
aws signer get-signing-profile \
  --profile-name lambda-signing-prod \
  --query 'signingMaterial.{CertificateArn:certificateArn}' \
  --output table --region us-east-1
```

**Key implication:** Signer rotates the certificate on its own
schedule. Do not cache the certificate indefinitely for offline
verification. Re-fetch via `GetSigningProfile` each time.

For a specific signing job, the certificate used at signing time is
recorded in `describe-signing-job`:

```bash
aws signer describe-signing-job \
  --job-id "$JOB_ID" \
  --query '{Signature:signature, SignedObject:signedObject, JobInvoker:jobInvoker, ProfileVersion:profileVersion}' \
  --output table --region us-east-1
```

## Revocation tracking

Revocation invalidates a profile version. Already-published Lambda
versions are NOT auto-rolled-back.

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

**Revoke playbook:**
1. Remove the revoked profile version's ARN from any CSC's
   `AllowedPublishingProfiles`.
2. Identify functions whose last successful deploy used that version
   (filter CloudTrail by the profile version).
3. Re-sign the deployment package under a new profile version
   (`StartSigningJob` with the new version).
4. Redeploy (`UpdateFunctionCode`) pointing at the new signed
   artifact in the destination prefix.
5. Verify the function's CSC association still allows the new
   version.

## CloudTrail audit

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
```

**Provenance reconstruction:** given a signed artifact in a Lambda
function, the provenance chain is:
1. CloudTrail `UpdateFunctionCode` event — gives the S3 source of
   the deploy.
2. The source S3 object matches the destination of a
   `StartSigningJob` event — gives the job ID, profile name, and
   profile version.
3. `PutSigningProfile` for that profile/version — gives the platform
   and the time of promotion.

## IAM for signing job submitters

Minimum IAM for a CI pipeline that submits signing jobs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "signer:StartSigningJob",
        "signer:DescribeSigningJob",
        "signer:ListSigningJobs",
        "signer:GetSigningProfile",
        "signer:PutSigningProfile"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::my-unsigned-artifacts/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::my-signed-artifacts/*"]
    }
  ]
}
```

Use resource ARNs to narrow `signer:*` permissions per profile in
multi-tenant CI.

## Common pitfalls

1. **Destination bucket missing Signer write grant.** The job fails
   with `Failed` status. Add the bucket policy granting
   `signer.amazonaws.com` `s3:PutObject` on the prefix.

2. **Polling too briefly.** Signer jobs for small Lambda zips are
   fast, but firmware images can take several minutes. Poll
   `describe-signing-job` until terminal state.

3. **Confusing source and destination in `UpdateFunctionCode`.**
   Lambda expects the SIGNED artifact in the destination prefix.
   Pointing at the unsigned source object fails signature
   verification under `Enforce`.

4. **Leaving the revoked ARN in the CSC.** A revoked version blocks
   new deploys (`Enforce`) but does NOT roll back already-published
   versions. Remove the ARN and redeploy.

5. **Caching the signing certificate.** Signer rotates the cert.
   Always re-fetch via `GetSigningProfile`.
