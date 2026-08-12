---
name: rolesanywhere-trust-deployer
description: >-
  Provisions IAM Roles Anywhere trust infrastructure with production
  defaults: trust anchor creation (binding an external certificate
  authority to AWS IAM), profile creation (mapping external
  certificates to IAM roles via role ARNs and role-passthrough),
  session policy attachment, credential helper configuration (AWS
  signing helper for certificate-based authentication), external CA
  (PKI) integration, role assumption workflow (exchange X.509
  certificate for STS temporary credentials), session duration,
  managed-policy vs inline-policy selection, temporary credentials
  (access key / secret / session token), CloudTrail audit
  (AssumeRoot events), and revocation configuration (CRL/OCSP).
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when creating a Roles Anywhere trust anchor, mapping external
  certificates to IAM roles, configuring the credential helper,
  setting up cert-based authentication to AWS APIs, or integrating
  an external PKI with AWS. Triggers: create roles anywhere trust
  anchor, iam roles anywhere profile, credential helper, certificate
  based authentication aws, external ca aws, exchange cert for sts,
  roles anywhere session policy, roles anywhere revocation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with iam,
  rolesanywhere, sts, cloudwatch, and cloudtrail access, plus the
  aws_signing_helper binary (downloaded from AWS) on the client
  machine. Works with Terraform aws_rolesanywhere_trust_anchor,
  aws_rolesanywhere_profile, and aws_rolesanywhere_crl resources
  and CloudFormation AWS::RolesAnywhere::TrustAnchor /
  AWS::RolesAnywhere::Profile templates.
keywords:
  - aws
  - iam
  - roles anywhere
  - trust anchor
  - certificate authority
  - pki
  - x.509
  - credential helper
  - signing helper
  - sts
  - temporary credentials
  - session policy
  - cloudops
  - deploy
  - security
  - revocation
  - crl
  - assume root
tags:
  - aws
  - iam
  - roles-anywhere
  - trust-anchor
  - certificate-authority
  - pki
  - credential-helper
  - cloudops
  - deploy
  - security
  - session-policy
  - revocation
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
    - iam
    - roles-anywhere
    - trust-anchor
    - certificate-authority
    - pki
    - credential-helper
    - cloudops
    - deploy
    - security
    - session-policy
    - revocation
  dependencies:
    - aws-orchestrator
  keywords:
    - create roles anywhere trust anchor
    - iam roles anywhere profile
    - credential helper
    - certificate based authentication aws
    - external ca aws
    - exchange cert for sts
    - roles anywhere session policy
    - roles anywhere revocation
  when_to_use: >-
    Invoke when the user wants to create an IAM Roles Anywhere trust
    anchor (binding an external certificate authority to AWS IAM),
    create a profile (mapping external certificates to IAM roles),
    configure the credential helper (AWS signing helper), set up
    certificate-based authentication to AWS APIs, integrate an
    external PKI with AWS, configure revocation (CRL/OCSP), or
    understand the role assumption workflow (exchange X.509 cert
    for STS credentials). Do NOT invoke for standard IAM role
    assumption via STS (no certificate), AWS IAM Identity Center
    (SSO), or AWS Organizations SCC (service control policies).
---

# Roles Anywhere Trust Deployer

An AWS CloudOps agent skill that provisions IAM Roles Anywhere trust
infrastructure with correct defaults. The skill walks the operator
through trust anchor creation (binding an external CA to AWS IAM),
profile creation (mapping external certificates to IAM roles), session
policy configuration, credential helper setup (AWS signing helper for
certificate-based authentication), role assumption workflow (exchanging
an X.509 certificate for STS temporary credentials), revocation
configuration (CRL/OCSP), and CloudTrail audit (AssumeRoot events). The
skill captures PKI and trust decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Roles Anywhere trust anchor, IAM Roles Anywhere profile,
credential helper, certificate-based authentication AWS, external CA
AWS, exchange cert for STS, Roles Anywhere session policy, Roles
Anywhere revocation.

## STRICT output contract

When this skill is invoked with a Roles-Anywhere-provisioning request
(create a trust anchor, create a profile, configure the credential
helper, set up cert-based authentication, integrate an external PKI,
or configure revocation), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `ROLES_ANYWHERE:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Trust anchor (bind external CA to AWS IAM) | Core trust model |
| Step 2 — Profile (map external cert to IAM role) | Role mapping |
| Step 3 — IAM role (trust policy for Roles Anywhere) | Permissions |
| Step 4 — Session policy | Session scoping |
| Step 5 — Credential helper (AWS signing helper) | Client-side auth |
| Step 6 — Role assumption workflow (exchange cert for STS) | End-to-end flow |
| Step 7 — Revocation configuration (CRL/OCSP) | Trust lifecycle |
| Step 8 — CloudTrail audit (AssumeRoot) | Compliance |
| Step 9 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/trust-anchor-and-profile.md | Trust anchor + profile detail |
| references/credential-helper-and-revocation.md | Helper + revocation detail |

## Mindset

**One-line takeaway:** IAM Roles Anywhere lets external workloads
(on-prem servers, CI runners, edge devices) assume IAM roles using
X.509 certificates from your own PKI instead of long-lived AWS access
keys. The trust anchor binds your external CA to AWS IAM; the profile
maps external certificates to IAM roles; the credential helper signs
AWS API requests with the certificate and obtains STS temporary
credentials. Without the trust anchor, AWS does not trust your CA.
Without the profile, AWS does not know which role to assume. Without
the credential helper, the workload cannot sign requests.

Three misconceptions dominate Roles Anywhere misdesign at provisioning
time:

- **"The trust anchor alone grants access."** It does not. The trust
  anchor only binds your external CA to AWS IAM — it tells AWS "trust
  certificates signed by this CA." A profile is ALSO required to map
  the certificate to an IAM role, and the IAM role's trust policy must
  allow `sts:AssumeRole` from `rolesanywhere.amazonaws.com` (or use
  `sts:SetSourceIdentity` and the `AssumeRoot` action). Without all
  three (trust anchor + profile + IAM role with correct trust policy),
  the credential helper fails to obtain credentials.

- **"Any certificate from the CA can assume any role."** It cannot.
  The profile's `roleArns` list (or role-passthrough mode) determines
  which IAM roles the certificate can assume. Even if the certificate
  is valid and signed by a trusted CA, the profile must explicitly
  list the role ARN. An over-permissive profile violates least
  privilege; an under-permissive one results in `AccessDenied`.

- **"Revocation is automatic."** It is not. By default, a certificate
  remains valid until its expiration date. To revoke before expiration,
  you must configure a Certificate Revocation List (CRL). Without
  revocation, a compromised certificate remains usable until it
  expires. This is the #1 cause of "we revoked the cert in the CA but
  AWS still accepts it" incidents.

## Configuration dependency graph (novel heuristic)

Roles Anywhere configurations are NOT independent. The trust anchor
must bind the CA before the profile can map certificates; the IAM
role's trust policy must allow Roles Anywhere before assume works; the
credential helper must reference the correct profile and certificate
before the workload can authenticate. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| External CA (PKI) | CA exists and can sign X.509 certificates | CA private key must be securely stored; CA cert must be in PEM format | trust anchor |
| Trust anchor | CA certificate in PEM format | trust anchor is immutable once created; to rotate the CA, create a new trust anchor and update the profile | AWS trusts certs from this CA |
| IAM role (trust policy) | role exists; trust policy allows `sts:AssumeRole` from `rolesanywhere.amazonaws.com` (or service principal for AssumeRoot) | without the trust policy, assume fails with `AccessDenied` — opaque to the client | role can be assumed via Roles Anywhere |
| IAM role (permissions) | role has permissions for the target AWS actions | over-permissive role violates least-privilege; under-permissive role causes API failures | temporary credentials have the right scope |
| Profile | trust anchor exists; roleArns reference valid IAM roles | role-passthrough mode lets the client specify the role ARN at assume time — use with caution | certificate-to-role mapping |
| Session policy | profile references a managed or inline session policy | session policy further restricts (never expands) the IAM role's permissions | scoped session |
| Credential helper | client certificate + private key + profile ID + trust anchor ID | helper signs requests with the certificate; without it, the client cannot authenticate | temporary credentials on the client |
| Revocation (CRL) | CRL endpoint reachable by Roles Anywhere; CRL signed by the CA | without revocation, compromised certs remain valid until expiration | compromised certs are rejected |
| CloudTrail audit | CloudTrail logging enabled in the account | AssumeRoot events are logged under the `AssumeRoot` event name in CloudTrail | compliance audit trail |

**The trust-policy-on-the-IAM-role row is the one a baseline model
misses.** A baseline says "create a trust anchor and profile." The
correct heuristic recognizes that the IAM role's trust policy must
explicitly allow `sts:AssumeRole` from `rolesanywhere.amazonaws.com`.
Without this trust policy, the credential helper returns
`AccessDenied` even with a valid certificate, trust anchor, and
profile.

**Cross-dependency gotchas:**
- A role that trusts only `ec2.amazonaws.com` (EC2 instance profile)
  CANNOT be assumed via Roles Anywhere — it must trust
  `rolesanywhere.amazonaws.com`.
- The profile's `roleArns` must match the IAM role ARN exactly. A
  mismatch (wrong path or wrong role name) causes assume to fail.
- The credential helper requires the certificate AND the private key —
  the helper signs the request with the private key to prove possession.
- Session policies RESTRICT permissions; they never expand them. A
  session policy cannot grant more than the IAM role's policies allow.
- Revocation (CRL) must be configured at the trust anchor level. A CRL
  applies to ALL certificates issued by the CA bound to that anchor.

## Expert heuristic: the three-legged trust stool

A baseline model says "create a trust anchor." The correct heuristic
recognizes that Roles Anywhere requires three components to function:

```text
Three-legged trust stool:
  1. Trust anchor (binds external CA to AWS IAM)
     → "AWS trusts certificates signed by this CA"
     → Without: AWS rejects all certificates from your PKI

  2. Profile (maps external certificate to IAM role)
     → "A certificate from this CA can assume these IAM roles"
     → Without: AWS does not know which role to assume

  3. IAM role (with trust policy for rolesanywhere.amazonaws.com)
     → "This role can be assumed by Roles Anywhere"
     → Without: assume fails with AccessDenied

All three must exist. Missing any one results in opaque failure — the
credential helper returns AccessDenied without indicating which is wrong.
```

**Key implication:** the #1 cause of "Roles Anywhere doesn't work" is a
missing or incorrect trust policy on the IAM role. Always verify the
role's trust policy includes `rolesanywhere.amazonaws.com` as a
principal.

## Expert heuristic: the credential helper signs requests with the certificate

The AWS signing helper (`aws_signing_helper`) is the client-side tool
that exchanges an X.509 certificate for STS temporary credentials,
signing the AssumeRole request with the certificate's private key to
prove possession.

```text
Credential helper workflow:
  1. Client has: certificate.pem, private-key.pem, profile-id, role-arn
  2. aws_signing_helper sign-request:
     → Reads the certificate and private key
     → Constructs an AssumeRole request
     → Signs the request with the private key
     → Sends to Roles Anywhere endpoint
  3. Roles Anywhere validates:
     → Certificate is signed by the trust anchor's CA
     → Certificate is not expired (and not revoked, if CRL is configured)
     → Profile maps the certificate to the requested role
     → IAM role's trust policy allows Roles Anywhere
  4. Roles Anywhere returns STS temporary credentials:
     → AccessKeyId, SecretAccessKey, SessionToken
     → Expiration (based on session duration)
  5. Client uses the temporary credentials to call AWS APIs
```

**Key implication:** the credential helper must run on the client
machine (the workload that needs AWS access). It is not an AWS service
— it is a binary you download from AWS and run locally. Without it,
the workload cannot sign requests with the certificate.

## Expert heuristic: session policies restrict, never expand

A session policy is an optional inline or managed policy attached to
the profile. It further restricts the IAM role's permissions for
sessions assumed via that profile. Effective permissions = IAM role
permissions intersected with the session policy. If the IAM role
allows `s3:*` and the session policy allows `s3:GetObject` only, the
effective permission is `s3:GetObject` only. If the IAM role allows
`s3:GetObject` and the session policy allows `s3:PutObject` only, the
effective permission is NOTHING (empty intersection).

**Key implication:** use session policies to scope down a shared IAM
role for different profiles. For example, a "ci-runner" role with
`s3:*` can have a profile with a session policy restricting it to
`s3:GetObject` on a specific bucket. The session policy cannot grant
more than the role allows.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| External CA exists with X.509 signing capability | Trust anchor binds the CA cert to AWS IAM | Verify CA cert in PEM format: `openssl x509 -in ca-cert.pem -text -noout` |
| Client certificate and private key generated | Credential helper needs both to sign requests | `openssl x509 -in client-cert.pem -text -noout` |
| IAM role exists with Roles Anywhere trust policy | Role must be assumable by `rolesanywhere.amazonaws.com` | `aws iam get-role --role-name <name>` and check trust policy |
| IAM role has appropriate permissions | Temporary credentials scope comes from the role | `aws iam list-attached-role-policies` and `aws iam list-role-policies` |
| Region supports Roles Anywhere | Available in most regions but verify | `aws rolesanywhere list-trust-anchors --region <region>` |
| aws_signing_helper downloaded (for client-side testing) | Client needs the helper to exchange cert for STS | Check binary on the client machine |
| CloudTrail logging enabled (for audit) | AssumeRoot events need CloudTrail to be recorded | `aws cloudtrail describe-trails` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Trust anchor (bind external CA to AWS IAM)

A trust anchor binds an external certificate authority (CA) to AWS IAM.
It tells AWS "trust X.509 certificates signed by this CA."

| Trust anchor field | Purpose | Required |
|---|---|---|
| `name` | Human-readable name | Yes |
| `source.sourceType` | Type of CA source (`CERTIFICATE_BUNDLE` for self-managed CA, `AWS_ACM_PCA` for AWS Private CA) | Yes |
| `source.sourceData.acmPcaArn` | ACM PCA ARN (if sourceType is `AWS_ACM_PCA`) | If using ACM PCA |
| `source.sourceData.x509CertificateData` | PEM-encoded CA certificate (if sourceType is `CERTIFICATE_BUNDLE`) | If using self-managed CA |
| `enabled` | Enable or disable the trust anchor | Yes (default: true) |
| `notificationSettings` | Notify on cert expiry, etc. | Optional |

**Create a trust anchor from a self-managed CA (CERTIFICATE_BUNDLE):**

```bash
CA_CERT=$(cat ca-cert.pem)

TRUST_ANCHOR_ID=$(aws rolesanywhere create-trust-anchor \
  --name "my-pki-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CA_CERT}" \
  --enabled \
  --region us-east-1 \
  --query 'trustAnchor.trustAnchorId' --output text)

echo "Trust anchor: $TRUST_ANCHOR_ID"
```

**Create a trust anchor from AWS Private CA (AWS_ACM_PCA):**

```bash
TRUST_ANCHOR_ID=$(aws rolesanywhere create-trust-anchor \
  --name "acm-pca-trust-anchor" \
  --source "sourceType=AWS_ACM_PCA,sourceData={acmPcaArn=arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/12345678-1234-1234-1234-123456789012}" \
  --enabled \
  --region us-east-1 \
  --query 'trustAnchor.trustAnchorId' --output text)
```

**Critical:** the trust anchor is immutable once created. To rotate
the CA, create a new trust anchor and update the profile to reference
it.

## Step 2 — Profile (map external cert to IAM role)

A profile maps an external certificate (validated via the trust anchor)
to one or more IAM roles.

| Profile field | Purpose | Required |
|---|---|---|
| `name` | Human-readable name | Yes |
| `trustAnchorId` | The trust anchor that validates the cert | Yes |
| `roleArns` | List of IAM role ARNs the cert can assume | Yes (unless using role-passthrough) |
| `durationSeconds` | Session duration (900-43200 seconds) | Yes (default: 3600) |
| `enabled` | Enable or disable the profile | Yes (default: true) |
| `sessionPolicy` | Inline session policy (further restricts permissions) | Optional |
| `managedPolicyArns` | Managed policy ARNs to apply as session policies | Optional |

**Create a profile:**

```bash
PROFILE_ID=$(aws rolesanywhere create-profile \
  --name "ci-runner-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --role-arns "arn:aws:iam::123456789012:role/RolesAnywhereCIRunner" \
  --duration-seconds 3600 \
  --enabled \
  --region us-east-1 \
  --query 'profile.profileId' --output text)

echo "Profile: $PROFILE_ID"
```

**Role-passthrough mode:** if `roleArns` is omitted, the profile uses
role-passthrough mode, where the client specifies the role ARN at
assume time. This is more flexible but less controlled. Use only when
the client should dynamically choose the role.

**Critical:** the `roleArns` list determines which roles the
certificate can assume. Listing too many roles violates least
privilege. List only the role(s) this specific workload needs.

## Step 3 — IAM role (trust policy for Roles Anywhere)

The IAM role must have a trust policy that allows Roles Anywhere to
assume it. This is the #1 forgotten step.

**Trust policy for Roles Anywhere:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceProfileArn": "arn:aws:rolesanywhere:us-east-1:123456789012:profile/<profile-id>"
        }
      }
    }
  ]
}
```

**Create the IAM role:**

```bash
aws iam create-role \
  --role-name RolesAnywhereCIRunner \
  --assume-role-policy-document file://trust-policy.json \
  --region us-east-1

aws iam attach-role-policy \
  --role-name RolesAnywhereCIRunner \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

**Critical:** without the trust policy allowing
`rolesanywhere.amazonaws.com`, the role CANNOT be assumed via Roles
Anywhere. The credential helper returns `AccessDenied`.

## Step 4 — Session policy

A session policy is an optional inline or managed policy attached to
the profile. It further restricts the IAM role's permissions for
sessions assumed via that profile.

**Inline session policy (restrict to a specific S3 bucket):**

```bash
aws rolesanywhere update-profile \
  --profile-id "$PROFILE_ID" \
  --session-policy file://session-policy.json \
  --region us-east-1
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-ci-artifacts/*"
    }
  ]
}
```

**Critical:** session policies RESTRICT permissions; they never expand
them. Effective permissions = IAM role permissions intersected with
the session policy.

## Step 5 — Credential helper (AWS signing helper)

The AWS signing helper (`aws_signing_helper`) is a client-side binary
that exchanges an X.509 certificate for STS temporary credentials.

**Download the signing helper** for your platform from the AWS Roles
Anywhere helper tool S3 bucket (e.g.,
`https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_darwin_arm64`),
then `chmod +x aws_signing_helper`.

**Exchange certificate for temporary credentials:**

```bash
./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --profile-id "$PROFILE_ID" \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1
```

This outputs JSON with `AccessKeyId`, `SecretAccessKey`, and
`SessionToken`. The client can then use these credentials to call AWS
APIs.

**Configure the AWS CLI to use the credential helper:**

```ini
[profile rolesanywhere]
credential_process = ./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id <trust-anchor-id> \
  --profile-id <profile-id> \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1
region = us-east-1
```

**Critical:** the credential helper must run on the client machine. It
is not an AWS service. Without it, the workload cannot sign requests.

## Step 6 — Role assumption workflow (exchange cert for STS)

End-to-end flow: the client generates a key pair and obtains a
certificate from the external CA, then runs `aws_signing_helper
credential-process` with `--certificate`, `--private-key`,
`--trust-anchor-id`, `--profile-id`, and `--role-arn`. The signing
helper sends the request to the Roles Anywhere endpoint, which
validates the certificate chain (signed by the trust anchor's CA, not
expired, not revoked if CRL is configured, profile maps the cert to the
requested role, IAM role's trust policy allows Roles Anywhere), then
returns STS temporary credentials. The client uses these credentials to
call AWS APIs; they expire after the session duration (default: 1 hour),
and the credential helper re-runs to refresh.

**Verify the temporary credentials work:**

```bash
# Use the credentials to list S3 buckets
AWS_PROFILE=rolesanywhere aws s3 ls

# Or export the credentials manually
eval "$(./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --profile-id "$PROFILE_ID" \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1 --output env)"

aws sts get-caller-identity
```

## Step 7 — Revocation configuration (CRL/OCSP)

By default, a certificate remains valid until its expiration date. To
revoke a certificate before expiration, configure a Certificate
Revocation List (CRL).

**Create a CRL:**

```bash
aws rolesanywhere enable-crl \
  --crl-name "my-pki-crl" \
  --crl-data "$(base64 crl.pem)" \
  --trust-anchor-arn "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/$TRUST_ANCHOR_ID" \
  --region us-east-1
```

**Update the CRL when certificates are revoked:**

```bash
# Regenerate the CRL in your CA after revoking a certificate
openssl ca -gencrl -out crl.pem

# Update the CRL in Roles Anywhere
aws rolesanywhere update-crl \
  --crl-id "$CRL_ID" \
  --crl-data "$(base64 crl.pem)" \
  --region us-east-1
```

**Critical:** without a CRL, a compromised certificate remains usable
until it expires. Always configure revocation for production PKIs.

## Step 8 — CloudTrail audit (AssumeRoot)

Roles Anywhere sessions are logged in CloudTrail under the `AssumeRoot`
event name (source: `rolesanywhere.amazonaws.com`). Key fields include
`requestParameters.profileArn`, `requestParameters.trustAnchorArn`, and
`requestParameters.roleArn`.

**Query CloudTrail for Roles Anywhere sessions:**

```bash
aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=EventName,AttributeValue=AssumeRoot" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region us-east-1 \
  --query 'Events[*].{Time:EventTime,User:Username,Role:EventName}' \
  --output table
```

## Step 9 — Recent features

**Recent AWS features (2023-2026):**

- **Roles Anywhere General Availability (2023):** IAM Roles Anywhere
  reached GA, enabling certificate-based authentication to AWS APIs
  for workloads outside of AWS.
- **ACM PCA integration (2023-2024):** Trust anchors can reference
  AWS Private Certificate Authority (ACM PCA) directly, simplifying
  CA management for AWS-native PKIs.
- **Session policies (2023-2024):** Profiles support inline and
  managed session policies, enabling per-profile permission scoping
  on a shared IAM role.
- **Role-passthrough mode (2023-2024):** Profiles can use role-
  passthrough mode, where the client specifies the role ARN at assume
  time (instead of the profile pre-listing role ARNs).
- **CRL revocation (2023-2024):** Certificate Revocation Lists (CRLs)
  can be attached to trust anchors, enabling revocation of compromised
  certificates before expiration.
- **Credential helper updates (2024-2025):** The AWS signing helper
  added `credential-process` output format (compatible with the AWS
  CLI credential process), and improved error messages.
- **Instance-based attribution (2024-2025):** Roles Anywhere sessions
  now include instance-based attribution in CloudTrail, making it
  easier to identify which workload assumed which role.
- **Cross-account trust anchors (2024-2025):** Trust anchors can be
  shared across accounts via AWS Resource Access Manager (RAM),
  enabling centralized PKI management.

## NEVER do these things

1. **NEVER assume the trust anchor alone grants access.** The trust
   anchor only binds the CA to AWS IAM. A profile AND an IAM role with
   the correct trust policy are ALSO required.

2. **NEVER use an IAM role without a Roles Anywhere trust policy.**
   The role's trust policy must allow `sts:AssumeRole` from
   `rolesanywhere.amazonaws.com`. Without it, assume fails with
   `AccessDenied`.

3. **NEVER list too many roles in a profile.** The `roleArns` list
   determines which roles the cert can assume. List only the role(s)
   this specific workload needs. Over-permissive profiles violate
   least privilege.

4. **NEVER skip revocation configuration.** Without a CRL, a
   compromised certificate remains usable until it expires. Always
   configure revocation for production PKIs.

5. **NEVER store the CA private key on the client machine.** The CA
   private key must be securely stored (HSM, KMS, or offline CA). Only
   the client certificate and its private key should be on the client.

6. **NEVER assume session policies expand permissions.** Session
   policies RESTRICT permissions; they never expand them. Effective
   permissions = IAM role permissions intersected with the session
   policy.

7. **NEVER use long-lived certificates without expiration.** Certificates
   should have a reasonable expiration (e.g., 90 days for CI runners,
   1 year for servers). Avoid 10-year certificates.

8. **NEVER forget the credential helper on the client.** The signing
   helper must be installed on the client; without it, the workload
   cannot sign requests with the certificate.

9. **NEVER assume role-passthrough is safe without controls.**
   Role-passthrough mode lets the client specify any role ARN at
   assume time. Use only when the client is fully trusted, or when
   the IAM roles' trust policies enforce strict Conditions.

10. **NEVER ignore CloudTrail audit events.** Roles Anywhere sessions
    are logged as `AssumeRoot` events. Regularly audit which
    certificates assumed which roles, especially after a certificate
    is compromised.

## Output format

```text
ROLES_ANYWHERE: <trust-anchor-id> → <profile-id> → <role-arn>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Trust anchor: <trust-anchor-id> — <ca-source> (CERTIFICATE_BUNDLE | AWS_ACM_PCA)
  [✓|✗] Profile: <profile-id> — roleArns: <role-arn list> (duration: <seconds>s)
  [✓|✗] IAM role: <role-arn> (trust: rolesanywhere.amazonaws.com; permissions: <description>)
  [✓|✗] Session policy: <inline|managed|none> — <description>
  [✓|✗] Credential helper: aws_signing_helper (client-side, cert: <cert-path>)
  [✓|✗] Revocation: CRL configured (<crl-name>) | Not configured
  [✓|✗] CloudTrail audit: AssumeRoot events logged
  [✓|✗] CA certificate verified: <ca-cert-path> (PEM, expires <date>)
  [✓|✗] Client certificate verified: <client-cert-path> (PEM, expires <date>)
  [✓|✗] Region: <region>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws rolesanywhere list-trust-anchors --region <region>
  aws rolesanywhere list-profiles --region <region>
  aws iam get-role --role-name <role-name>
  ./aws_signing_helper credential-process --certificate <cert> --private-key <key> --trust-anchor-id <id> --profile-id <id> --role-arn <arn> --region <region>
```

### Worked example — CI runner with external PKI

```text
ROLES_ANYWHERE: ta-aaa111222 → p-bbb222333 → arn:aws:iam::123456789012:role/RolesAnywhereCIRunner
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Trust anchor: ta-aaa111222 — self-managed CA (CERTIFICATE_BUNDLE, ca-cert.pem)
  [✓] Profile: p-bbb222333 — roleArns: arn:aws:iam::123456789012:role/RolesAnywhereCIRunner (duration: 3600s)
  [✓] IAM role: arn:aws:iam::123456789012:role/RolesAnywhereCIRunner (trust: rolesanywhere.amazonaws.com; permissions: AmazonS3ReadOnlyAccess)
  [✓] Session policy: inline — restrict to s3:GetObject on my-ci-artifacts/*
  [✓] Credential helper: aws_signing_helper (client-side, cert: client-cert.pem)
  [✓] Revocation: CRL configured (my-pki-crl)
  [✓] CloudTrail audit: AssumeRoot events logged
  [✓] CA certificate verified: ca-cert.pem (PEM, expires 2027-12-31)
  [✓] Client certificate verified: client-cert.pem (PEM, expires 2026-11-01)
  [✓] Region: us-east-1
  [✓] Tags: Environment=production, Workload=ci-runner
VERIFICATION_COMMANDS:
  aws rolesanywhere list-trust-anchors --region us-east-1
  aws rolesanywhere list-profiles --region us-east-1
  aws iam get-role --role-name RolesAnywhereCIRunner
  ./aws_signing_helper credential-process --certificate client-cert.pem --private-key client-key.pem --trust-anchor-id ta-aaa111222 --profile-id p-bbb222333 --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner --region us-east-1
```

## Error handling

### AccessDenied when assuming a role
- The IAM role's trust policy does not allow
  `rolesanywhere.amazonaws.com`. Verify the trust policy. Also verify
  the profile's `roleArns` includes the requested role ARN.

### Certificate rejected: not signed by trusted CA
- The certificate is not signed by the CA bound to the trust anchor.
  Verify the chain: `openssl verify -CAfile ca-cert.pem client-cert.pem`.
  Also verify the trust anchor's CA cert matches.

### Certificate rejected: expired or revoked
- The certificate has passed its expiration date (generate a new one)
  or is on the CRL (remove from the CRL and update if accidental).

### Credential helper not found
- The `aws_signing_helper` binary is not on the client machine.
  Download it from the AWS Roles Anywhere helper tool S3 bucket.

### Session expires too quickly
- The session duration is too short. Update the profile's
  `durationSeconds` (max: 43200 seconds = 12 hours). The credential
  helper re-runs automatically if configured as a credential process.

## Domain

AWS CloudOps / IAM Roles Anywhere Trust Infrastructure Provisioning &
Certificate-Based Authentication.

## AWS documentation

- **IAM Roles Anywhere User Guide** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html
- **Create trust anchor** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/trust-anchors.html
- **Create profile** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/profiles.html
- **Credential helper** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html
- **Revocation (CRL)** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/revocation.html
- **CloudTrail audit** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/security-logging.html
- **AWS CLI rolesanywhere** — https://docs.aws.amazon.com/cli/latest/reference/rolesanywhere/
- **IAM Roles Anywhere best practices** — https://docs.aws.amazon.com/rolesanywhere/latest/userguide/best-practices.html
