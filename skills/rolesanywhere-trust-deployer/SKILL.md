---
name: rolesanywhere-trust-deployer
description: 'Provisions IAM Roles Anywhere trust infrastructure with production defaults: trust anchor creation (binding an external certificate authority to AWS IAM), profile creation (mapping external certificates to IAM roles via role ARNs and role-passthrough), session policy attachment, credential helper configuration (AWS signing helper for certificate-based authentication), external CA (PKI) integration, role assumption workflow (exchange X.509 certificate for STS temporary credentials), session duration, managed-policy vs inline-policy selection, temporary credentials (access key / secret / session token), CloudTrail audit (AssumeRoot events), and revocation configuration (CRL/OCSP). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Roles Anywhere trust. Triggers: create roles anywhere trust anchor, iam roles anywhere profile, credential helper, certificate based authentication aws, external ca aws, exchange cert for sts, roles anywhere session policy, roles anywhere revocation.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with iam, rolesanywhere, sts, cloudwatch, and cloudtrail access, plus the aws_signing_helper binary (downloaded from AWS) on the client machine. Works with Terraform aws_rolesanywhere_trust_anchor, aws_rolesanywhere_profile, and aws_rolesanywhere_crl resources and CloudFormation AWS::RolesAnywhere::TrustAnchor / AWS::RolesAnywhere::Profile templates.'
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
  tags: aws, iam, roles-anywhere, trust-anchor, certificate-authority, pki, credential-helper, cloudops, deploy, security, session-policy, revocation
  dependencies: aws-orchestrator
  keywords: aws, iam, roles anywhere, trust anchor, certificate authority, pki, x.509, credential helper, signing helper, sts, temporary credentials, session policy, cloudops, deploy, security, revocation, crl, assume root
  when_to_use: Invoke when the user wants to create an IAM Roles Anywhere trust anchor (binding an external certificate authority to AWS IAM), create a profile (mapping external certificates to IAM roles), configure the credential helper (AWS signing helper), set up certificate-based authentication to AWS APIs, integrate an external PKI with AWS, configure revocation (CRL/OCSP), or understand the role assumption workflow (exchange X.509 cert for STS credentials). Do NOT invoke for standard IAM role assumption via STS (no certificate), AWS IAM Identity Center (SSO), or AWS Organizations SCC (service control policies).
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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#common-misconceptions-from-mindset).
> Three trust-model misconceptions: anchor-alone access, any-cert-any-role, automatic revocation.

## Configuration dependency graph (novel heuristic)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-sequencing-notes).
> Sequencing table, the IAM trust-policy trap, and cross-dependency gotchas.

## Expert heuristic: the three-legged trust stool

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-the-three-legged-trust-stool).
> Trust anchor + profile + IAM role trust policy; missing any one fails opaquely.

## Expert heuristic: the credential helper signs requests with the certificate

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-the-credential-helper-signs-requests-with-the-certificate).
> credential-process workflow: sign the AssumeRole request with the cert private key, receive STS credentials.

## Expert heuristic: session policies restrict, never expand

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-session-policies-restrict-never-expand).
> Effective permissions = role ∩ session policy; use to scope a shared role per profile.

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

> Moved to [references/credential-helper-and-revocation.md](references/credential-helper-and-revocation.md#signing-helper-download-and-aws-cli-integration-from-skillmd).
> Where to download aws_signing_helper per platform.

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

> Moved to [references/credential-helper-and-revocation.md](references/credential-helper-and-revocation.md#signing-helper-download-and-aws-cli-integration-from-skillmd).
> AWS CLI credential_process profile block wired to the signing helper.

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

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#verify-the-temporary-credentials-work-step-6).
> Use the assumed credentials: AWS_PROFILE=rolesanywhere aws s3 ls / sts get-caller-identity.

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

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#query-cloudtrail-for-roles-anywhere-sessions-step-8).
> cloudtrail lookup-events for AssumeRoot sessions in the last hour.

## Step 9 — Recent features

**Recent AWS features (2023-2026):**

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2023-2026).
> GA, ACM PCA anchors, session policies, role-passthrough, CRLs, helper updates, attribution, cross-account anchors.
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

> Moved to [references/error-handling.md](references/error-handling.md#error-handling).
> AccessDenied, cert not trusted, expired/revoked cert, helper missing, short sessions.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — misconceptions, dependency graph, expert heuristics, recent features
- [diagnostic-commands](references/diagnostic-commands.md) — credential verification and CloudTrail audit queries
- [error-handling](references/error-handling.md) — symptom-by-symptom troubleshooting
- [trust-anchor-and-profile](references/trust-anchor-and-profile.md) — trust anchor + profile detail (existing)
- [credential-helper-and-revocation](references/credential-helper-and-revocation.md) — helper setup, CRL revocation, CLI integration (existing)

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
