# Advanced Patterns — signer-signing-profile-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

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

