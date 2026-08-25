---
name: acm-private-ca-deployer
description: 'Provisions AWS Private Certificate Authority (ACM PCA) with production defaults: CA creation (root vs subordinate), key algorithm (RSA_2048, EC_prime256v1), signing algorithm (SHA256withRSA, SHA256withECDSA), CRL configuration (S3 bucket, expiration, CNAME), certificate template selection, CA certificate issuance (self-signed root vs parent-signed subordinate), certificate revocation, audit via CloudTrail, CA deletion (7-30 day mandatory waiting period), CA permissions for ACM integration, and OCSP support. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a private CA, issuing private certificates, configuring CRL revocation, setting up subordinate CA hierarchies, integrating ACM PCA with ACM, or deleting a private CA. Triggers: create private certificate authority, acm pca root ca, acm pca subordinate ca, issue private certificate, crl configuration s3, revoke certificate acm pca, ca deletion waiting period, acm pca permissions, acm managed private cert.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with acm-pca and acm access. Works with Terraform aws_acmpca_certificate_authority / aws_acmpca_certificate / aws_acmpca_certificate_authority_certificate resources and CloudFormation AWS::ACMPCA::CertificateAuthority / AWS::ACMPCA::Certificate templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, acm-pca, private-ca, cloudops, deploy, security, provisioning, pki, certificates, crl, revocation
  dependencies: aws-orchestrator
  keywords: aws, acm, acm pca, private certificate authority, private ca, cloudops, deploy, provisioning, root ca, subordinate ca, certificate, crl, ocsp, revocation, pki
  when_to_use: Invoke when the user wants to create a private certificate authority (root or subordinate), issue private certificates, configure CRL revocation, set up a subordinate CA hierarchy, integrate ACM PCA with ACM for managed certificate lifecycle, delete a private CA, or revoke certificates. Do NOT invoke for public TLS certificates (use ACM public certificate skills), AWS Certificate Manager public issuance, or AWS Secrets Manager certificate storage.
---

# ACM Private CA Deployer

An AWS CloudOps agent skill that provisions AWS Private Certificate
Authority (ACM PCA) with correct defaults. The skill walks the operator
through root vs subordinate CA creation, key and signing algorithm
selection, CRL configuration, certificate issuance, CA permissions for
ACM integration, certificate revocation, and the mandatory CA deletion
waiting period. It captures hierarchy decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create private certificate authority, ACM PCA root CA, ACM PCA
subordinate CA, issue private certificate, CRL configuration S3, revoke
certificate ACM PCA, CA deletion waiting period, ACM PCA permissions,
ACM managed private cert.

## STRICT output contract

When this skill is invoked with an ACM PCA provisioning request (create
a private CA, issue a certificate, configure CRL, set up a subordinate
hierarchy, delete a CA, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `ACM_PCA:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — CA type: root vs subordinate | Core CA model |
| Step 2 — Key and signing algorithm selection | Cryptographic choice |
| Step 3 — CRL configuration (S3 bucket) | Revocation infrastructure |
| Step 4 — Create the CA and issue CA certificate | Provisioning step |
| Step 5 — Certificate templates and end-entity issuance | Certificate issuance |
| Step 6 — CA permissions for ACM integration | Cross-account / ACM managed certs |
| Step 7 — Certificate revocation and OCSP | Revocation lifecycle |
| Step 8 — CA deletion (mandatory waiting period) | Decommissioning |
| Step 9 — Audit via CloudTrail | Compliance |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/ca-hierarchy-and-signing.md | Root/subordinate detail |
| references/crl-and-revocation.md | CRL + revocation detail |
| references/advanced-patterns.md | Expert-heuristic deep dives + recent features |
| references/error-handling.md | Error remedies |

## Mindset

**One-line takeaway:** ACM PCA provides managed private CAs. A root CA
is self-signed; a subordinate CA is signed by its parent CA and MUST
have the parent's permission to issue. CRL revocation requires an S3
bucket with a policy granting the ACM PCA service principal write
access. CA deletion is NOT immediate — it enters a mandatory 7-30 day
waiting period before permanent deletion.

Three misconceptions dominate ACM PCA misdesign at provisioning time:

- **"Creating the CA is enough to issue certificates."** It is not. A
  newly created CA is in `PENDING_CERTIFICATE` status. For a root CA,
  you must issue and import a self-signed certificate. For a
  subordinate CA, you must request a certificate from the parent CA,
  then import it. Until the CA is `ACTIVE`, no certificates can be
  issued from it.

- **"CRL works automatically without an S3 bucket policy."** It does
  not. The CRL distribution point requires an S3 bucket where ACM PCA
  publishes the CRL. The bucket MUST have a policy granting the
  `acm-pca.amazonaws.com` service principal `s3:PutObject` permission.
  Without this policy, CRL publication silently fails and clients
  cannot check revocation status.

- **"CA deletion is instant."** It is NOT. Deleting a CA initiates a
  mandatory waiting period of 7 to 30 days (you choose the duration).
  During this period the CA is in `DELETED` status but can be restored.
  After the period expires, the CA and all its data are permanently
  destroyed. This waiting period exists because certificates issued
  by the CA may still be in use.

## Configuration dependency graph (novel heuristic)

ACM PCA configurations are NOT independent. The CA must be ACTIVE
before issuing certificates. CRL requires an S3 bucket with the correct
policy. Subordinate CAs require parent CA permission. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| CA creation (root) | Key alg, signing alg, subject DN | CA is `CREATING` then `PENDING_CERTIFICATE`; NOT usable until `ACTIVE` | the CA ARN |
| CA creation (subordinate) | Key alg, signing alg, subject DN, parent CA ARN | CA is `PENDING_CERTIFICATE` until parent signs it; parent MUST have `create-permission` | subordinate CA |
| CA certificate (root) | CA created; CSR obtained | Root CA cert is self-signed; must issue then import | `ACTIVE` status |
| CA certificate (subordinate) | Subordinate CA created; CSR obtained; parent CA `ACTIVE` | Parent CA must issue subordinate cert; then import into subordinate | subordinate `ACTIVE` status |
| CRL configuration | S3 bucket exists | Bucket MUST have policy granting `acm-pca.amazonaws.com` `s3:PutObject`; without it CRL publication silently fails | revocation checking |
| End-entity certificate | CA `ACTIVE`; certificate template ARN | Template determines key usage, path length, validity; wrong template = wrong certificate | private TLS certificate |
| ACM integration | CA `ACTIVE`; `create-permission` granting ACM service principal | Without permission, ACM cannot request/renew certs from the CA | managed private cert lifecycle |
| CA deletion | CA exists | 7-30 day mandatory waiting period; restorable until period expires | decommissioning |

**The subordinate-parent-permission row is the one a baseline model
misses.** Creating a subordinate CA is not enough — the parent CA must
have a permission entry (`create-permission`) granting the requesting
principal the right to issue. Without it, the subordinate CA cannot be
signed by the parent and stays in `PENDING_CERTIFICATE` forever.

**Cross-dependency gotchas:**
- A subordinate CA requires the parent CA to be `ACTIVE` AND to have a
  `create-permission` entry. Both conditions must be met.
- CRL publication requires the S3 bucket policy to grant
  `acm-pca.amazonaws.com` write access. Missing the policy is a silent
  failure — the CA appears to work, but CRL is never published.
- ACM integration requires BOTH the CA to be `ACTIVE` AND a
  `create-permission` granting the ACM service principal access.
- CA deletion is reversible during the waiting period via
  `restore-certificate-authority`. After the period, it is permanent.

## Expert heuristic: root vs subordinate CA hierarchy

Full hierarchy decision tree (root self-sign vs subordinate parent-sign flows): moved to [references/advanced-patterns.md](references/advanced-patterns.md); command-level detail in [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

## Expert heuristic: CRL S3 bucket policy

CRL prerequisite checklist and silent-failure mode: moved to [references/advanced-patterns.md](references/advanced-patterns.md); bucket setup commands in [references/crl-and-revocation.md](references/crl-and-revocation.md).

## Expert heuristic: CA deletion waiting period

Deletion flow and restore semantics: moved to [references/advanced-patterns.md](references/advanced-patterns.md); delete/restore commands in [references/crl-and-revocation.md](references/crl-and-revocation.md).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Key algorithm chosen | Determines CA key type | Confirm in plan |
| Signing algorithm chosen | Must be compatible with key algorithm | Confirm in plan |
| Subject distinguished name (DN) | Required for CA creation | Confirm subject |
| S3 bucket for CRL (if CRL enabled) | CRL publication requires a writable bucket | `aws s3api head-bucket --bucket <name>` |
| CRL bucket policy grants PCA access | Without it CRL publication silently fails | `aws s3api get-bucket-policy --bucket <name>` |
| Parent CA ACTIVE (for subordinate) | Subordinate CA requires parent signing | `aws acm-pca describe-certificate-authority --certificate-authority-arn <parent-arn>` |
| Parent CA create-permission (for subordinate) | Parent must grant permission to issue | `aws acm-pca list-permissions --certificate-authority-arn <parent-arn>` |
| Certificate template identified | Template determines cert type, key usage, path length | Confirm template ARN |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — CA type: root vs subordinate

| Feature | Root CA | Subordinate CA |
|---|---|---|
| Certificate source | Self-signed | Signed by parent CA |
| Template for CA cert | `RootCACertificate/V1` | `SubordinateCACertificate/PathLen0/V1` |
| Trust anchor | Yes (clients trust directly) | No (clients trust root above it) |
| Requires parent CA | No | Yes (parent ACTIVE + permission) |
| Typical use | Offline root, trust anchor | Intermediate CA for daily cert issuance |

**Best practice:** use a root CA as the offline trust anchor and
subordinate CAs for active certificate issuance. This limits root CA
exposure.

## Step 2 — Key and signing algorithm selection

| Key algorithm | Valid signing algorithms | Notes |
|---|---|---|
| `RSA_2048` | `SHA256withRSA`, `SHA384withRSA`, `SHA512withRSA` | Default for most CAs |
| `RSA_4096` | `SHA256withRSA`, `SHA384withRSA`, `SHA512withRSA` | Root CAs requiring extra margin |
| `EC_prime256v1` | `SHA256withECDSA`, `SHA384withECDSA`, `SHA512withECDSA` | High-throughput subordinate CAs |
| `EC_secp384r1` | `SHA256withECDSA`, `SHA384withECDSA`, `SHA512withECDSA` | Stronger EC |

**Default:** `SHA256withRSA` for RSA keys, `SHA256withECDSA` for EC
keys. These have the broadest client compatibility.

## Step 3 — CRL configuration (S3 bucket)

Bucket creation and PCA bucket-policy commands: [references/crl-and-revocation.md](references/crl-and-revocation.md).

## Step 4 — Create the CA and issue CA certificate

create-certificate-authority commands (root + subordinate): [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

Root CA activation commands (CSR -> self-signed issue -> import): [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

Subordinate CA activation commands (parent signs CSR -> import chain): [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

**Verify CA is ACTIVE:**

```bash
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --query 'CertificateAuthority.Status' --region us-east-1
# Expected: ACTIVE
```

**Common mistake:** assuming the CA is immediately usable. After
creation, the CA is in `PENDING_CERTIFICATE`. It must receive its CA
certificate to become `ACTIVE`.

## Step 5 — Certificate templates and end-entity issuance

| Template ARN suffix | Purpose | Path length |
|---|---|---|
| `RootCACertificate/V1` | Self-signed root CA certificate | N/A |
| `SubordinateCACertificate_PathLen0/V1` | Subordinate CA (cannot issue further CA certs) | 0 |
| `SubordinateCACertificate_PathLen1/V1` | Subordinate CA (can issue one more level) | 1 |
| `EndEntityCertificate/CertPassedPathLen/0` | End-entity TLS certificate | N/A |
| `EndEntityCertificate/V1` | Basic end-entity certificate | N/A |
| `CodeSigningCertificate/V1` | Code signing certificate | N/A |
| `OCSPSigningCertificate/V1` | OCSP responder signing | N/A |

issue-certificate end-entity command: [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

## Step 6 — CA permissions for ACM integration

To let AWS Certificate Manager (ACM) request, issue, and renew private
certificates from a PCA, grant the ACM service principal permission.

```bash
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal acm.amazonaws.com \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

Cross-account create-permission command: [references/ca-hierarchy-and-signing.md](references/ca-hierarchy-and-signing.md).

## Step 7 — Certificate revocation and OCSP

revoke-certificate and OCSP enable commands: [references/crl-and-revocation.md](references/crl-and-revocation.md).

## Step 8 — CA deletion (mandatory waiting period)

delete/restore-certificate-authority commands: [references/crl-and-revocation.md](references/crl-and-revocation.md).

## Step 9 — Audit via CloudTrail

All ACM PCA API calls are logged to CloudTrail, providing a full audit
trail.

| Event | Security significance |
|---|---|
| `CreateCertificateAuthority` | New CA created |
| `IssueCertificate` | Certificate issued (who, what, template) |
| `ImportCertificateAuthorityCertificate` | CA activated |
| `RevokeCertificate` | Certificate revoked (who, why, serial) |
| `DeleteCertificateAuthority` | CA deletion initiated (waiting period started) |
| `CreatePermission` | Permission granted |
| `DeletePermission` | Permission revoked |

## Step 10 — Recent features

Full feature list with dates: [references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER assume the CA is usable immediately after creation.** The
   CA starts in `PENDING_CERTIFICATE`. It must receive its CA
   certificate to become `ACTIVE`.

2. **NEVER create a subordinate CA without verifying the parent CA is
   ACTIVE and has `create-permission`.** Without permission, the
   subordinate stays `PENDING_CERTIFICATE` indefinitely.

3. **NEVER configure CRL without the S3 bucket policy.** CRL
   publication silently fails without the policy granting
   `acm-pca.amazonaws.com` write access. Revoked certs appear valid.

4. **NEVER delete a CA without understanding the waiting period.**
   Deletion enters a mandatory 7-30 day period. After expiration, the
   CA is permanently destroyed and existing certs cannot be revoked.

5. **NEVER use the wrong certificate template.** Templates define key
   usage, extended key usage, and path length. Wrong template = wrong
   certificate extensions.

6. **NEVER forget to set up ACM permissions for managed cert lifecycle.**
   Without `create-permission` for `acm.amazonaws.com`, ACM cannot
   request or renew private certificates.

7. **NEVER assume OCSP replaces CRL.** Some clients only support CRL.
   Enable both for maximum client compatibility.

8. **NEVER issue certificates from a root CA for daily operations.**
   Use subordinate CAs for active issuance. Root CAs should be the
   offline trust anchor.

9. **NEVER revoke a certificate without recording the serial.** The
   certificate serial is required for revocation. Always record issued
   certificate serials in an asset inventory.

10. **NEVER assume CA deletion is instant.** The mandatory waiting
    period is 7-30 days. Plan decommissioning timelines accordingly.

## Output format (STRICT output contract)

When this skill is invoked with an ACM PCA provisioning request, the
agent MUST respond with the block below using the literal all-caps
labels `ACM_PCA:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### Decision tree — CA provisioning flow

```text
Need a private CA?
├── Need a self-signed trust anchor?
│     → ROOT CA
│       ├── Key: RSA_2048 (default) | RSA_4096 | EC_prime256v1 | EC_secp384r1
│       ├── Signing: SHA256withRSA (RSA) | SHA256withECDSA (EC)
│       ├── Template: RootCACertificate/V1
│       ├── CRL? → YES: create S3 bucket + policy → configure CrlConfiguration
│       │          NO: skip (OCSP only or none)
│       ├── ACM integration? → YES: create-permission for acm.amazonaws.com
│       └── Activate: self-sign → import-certificate-authority-certificate
│
├── Need a CA signed by an existing parent?
│     → SUBORDINATE CA
│       ├── PREREQUISITE: parent CA ACTIVE + has create-permission
│       ├── Template: SubordinateCACertificate_PathLen0/V1
│       └── Activate: parent signs CSR → import into subordinate
│
└── Need to issue end-entity certs (TLS)?
      → CA (root or subordinate) must be ACTIVE
      → Template: EndEntityCertificate/CertPassedPathLen/0
      → For ACM-managed lifecycle: create-permission for acm.amazonaws.com
```

### Output template

```text
ACM_PCA: <ca-name> (<ROOT|SUBORDINATE>, <key-algorithm>, <signing-algorithm>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] CA type: ROOT | SUBORDINATE
  [✓|✗] Key algorithm: RSA_2048 | RSA_4096 | EC_prime256v1 | EC_secp384r1
  [✓|✗] Signing algorithm: SHA256withRSA | SHA256withECDSA | ...
  [✓|✗] Subject DN: CN=<cn>, O=<org>, C=<country>
  [✓|✗] CRL S3 bucket: <bucket-name> — exists
  [✓|✗] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject
  [✓|✗] CRL expiration: <days> days, CustomCname: <cname|none>
  [✓|✗] OCSP: enabled | disabled
  [✓|✗] CA status: CREATING | PENDING_CERTIFICATE | ACTIVE
  [✓|✗] CA certificate: self-signed (root) | parent-signed (subordinate, parent <parent-arn>)
  [✓|✗] Certificate template: <template-arn-suffix>
  [✓|✗] ACM integration: create-permission for acm.amazonaws.com (IssueCertificate, GetCertificate, ListPermissions)
  [✓|✗] Parent CA permission: create-permission granted (for subordinate only)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws acm-pca describe-certificate-authority --certificate-authority-arn <ca-arn> --region <region>
  aws acm-pca list-permissions --certificate-authority-arn <ca-arn> --region <region>
  aws s3api get-bucket-policy --bucket <crl-bucket>
```

### FORBIDDEN NEVER patterns (output contract)

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without confirming CA status
   is `ACTIVE`.** A CA in `PENDING_CERTIFICATE` cannot issue
   certificates. The checklist MUST show `CA status: ACTIVE` with `[✓]`.

2. **NEVER mark CRL as `[✓]` without confirming the S3 bucket policy.**
   CRL publication silently fails without the policy granting
   `acm-pca.amazonaws.com` `s3:PutObject`. The checklist MUST show both
   the bucket name AND the policy status as verified.

3. **NEVER mark ACM integration as `[✓]` without confirming
   `create-permission` for `acm.amazonaws.com`.** Without this
   permission, ACM cannot request or renew private certificates. The
   verification MUST include `list-permissions` output.

4. **NEVER show a subordinate CA as `READY_TO_DEPLOY` without confirming
   the parent CA is `ACTIVE` and has `create-permission`.** A
   subordinate without parent signing stays `PENDING_CERTIFICATE`
   indefinitely. Both conditions (parent ACTIVE AND permission granted)
   must be met.

5. **NEVER omit the certificate template from the checklist.** The
   template determines key usage, extended key usage, and path length.
   A missing or wrong template produces a certificate with incorrect
   extensions that may be rejected by clients.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason citing
   what is missing and how to fix it. A bare `[✗]` with no explanation
   is non-compliant.

### Perfect worked example — root CA with RSA_2048, CRL, and ACM end-entity issuance

```text
ACM_PCA: Example Root CA (ROOT, RSA_2048, SHA256withRSA)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] CA type: ROOT
  [✓] Key algorithm: RSA_2048
  [✓] Signing algorithm: SHA256withRSA
  [✓] Subject DN: CN=Example Root CA, O=Example Org, C=US
  [✓] CRL S3 bucket: acm-pca-crl-123456789012-us-east-1 — exists
  [✓] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject, s3:PutObjectAcl, s3:GetBucketAcl, s3:GetBucketLocation
  [✓] CRL expiration: 7 days, CustomCname: crl.example.com
  [✓] OCSP: enabled (OCSP + CRL both active for maximum client compatibility)
  [✓] CA status: ACTIVE
  [✓] CA certificate: self-signed (RootCACertificate/V1 template, validity 10 years)
  [✓] Certificate template: RootCACertificate/V1 (CA cert); EndEntityCertificate/CertPassedPathLen/0 (end-entity issuance)
  [✓] ACM integration: create-permission for acm.amazonaws.com — IssueCertificate, GetCertificate, ListPermissions granted
  [✓] Tags: Environment=production, Purpose=trust-anchor, Owner=platform-team
VERIFICATION_COMMANDS:
  aws acm-pca describe-certificate-authority --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws acm-pca list-permissions --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws s3api get-bucket-policy --bucket acm-pca-crl-123456789012-us-east-1
  aws acm-pca get-certificate-authority-certificate --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
```

**How this example maps to provisioning steps:**

1. Created S3 bucket `acm-pca-crl-123456789012-us-east-1` for CRL.
2. Applied bucket policy granting `acm-pca.amazonaws.com` write access.
3. Created ROOT CA with `RSA_2048` / `SHA256withRSA`, CRL enabled (7-day
   expiration, CNAME `crl.example.com`), OCSP enabled.
4. Obtained CSR, issued self-signed certificate using
   `RootCACertificate/V1` template (10-year validity).
5. Imported the certificate to activate the CA (`ACTIVE` status).
6. Granted `create-permission` to `acm.amazonaws.com` so ACM can request
   end-entity certificates using `EndEntityCertificate/CertPassedPathLen/0`
   template.

**Self-check before emit:**
- [ ] CA status confirmed ACTIVE (not PENDING_CERTIFICATE)?
- [ ] CRL bucket policy grants acm-pca.amazonaws.com s3:PutObject?
- [ ] ACM create-permission confirmed via list-permissions?
- [ ] Certificate template correct for the CA type?
- [ ] For subordinate: parent CA ACTIVE + create-permission confirmed?

## Error handling

Error remedies (stuck PENDING_CERTIFICATE, parent will not sign, CRL not publishing, ACM access denied, deletion delay): [references/error-handling.md](references/error-handling.md).

## Domain

AWS CloudOps / AWS Private Certificate Authority (ACM PCA) Provisioning
& PKI Management.

## References (load on demand)

- [CA hierarchy and signing](references/ca-hierarchy-and-signing.md) — full root/subordinate provisioning and activation flows, end-entity issuance, ACM + cross-account permissions, Terraform
- [CRL and revocation](references/crl-and-revocation.md) — CRL bucket setup and policy, revocation + OCSP commands, CA deletion/restore, CloudTrail auditing
- [Advanced patterns](references/advanced-patterns.md) — expert heuristics (hierarchy decision tree, CRL bucket policy, deletion waiting period), recent AWS features
- [Error handling](references/error-handling.md) — stuck-state and access-denied remedies

## AWS documentation

- **ACM PCA User Guide** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html
- **Create a CA** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaCreateCa.html
- **Issue a certificate** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaIssueCert.html
- **CRL configuration** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaPlanDistribution.html
- **OCSP configuration** — https://docs.aws.amazon.com/privateca/latest/userguide/ocsp.html
- **CA permissions** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaCreatePerms.html
- **Certificate templates** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaTemplates.html
- **CA deletion** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaDeleteCa.html
- **ACM integration** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaIntegration.html
- **Revocation** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaRevoke.html
