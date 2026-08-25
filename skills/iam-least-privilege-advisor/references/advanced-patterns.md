# Advanced Patterns — IAM Least-Privilege Advisor

Expert edge-case catalog and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Expert edge cases (from SKILL.md § Expert edge cases)

### S3 dual-ARN requirement

S3 bucket actions and object actions use **different ARN shapes**, and a
correct policy must grant both:

- **Bucket-level actions** (e.g., `s3:ListBucket`, `s3:DeleteBucket`,
  `s3:GetBucketLocation`) require `arn:aws:s3:::bucket-name` (no trailing `/*`).
- **Object-level actions** (e.g., `s3:GetObject`, `s3:PutObject`,
  `s3:DeleteObject`) require `arn:aws:s3:::bucket-name/*` (with trailing `/*`).

A policy granting `s3:GetObject` on `arn:aws:s3:::bucket-name` (without `/*`)
silently fails — the action never matches. Conversely, granting `s3:*` on
both ARNs to "fix" the mismatch grants destructive bucket-level actions.
Classify such mismatches as **AMBIGUOUS** (the policy does not work as
written, but broadening it introduces over-permission).

### Scoping PassRole with `iam:PassedToService`

The safest way to scope `iam:PassRole` is not just to a specific role ARN
but also via the `iam:PassedToService` condition key, which restricts
*which AWS service* may receive the role:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/app-execution-role",
  "Condition": {
    "StringEquals": { "iam:PassedToService": "lambda.amazonaws.com" }
  }
}
```

This prevents the role from being passed to EC2, CloudFormation, or any
other service that accepts role ARNs. Without this condition, a principal
with `iam:PassRole` on a specific role can still pass it to any service,
potentially escalating via a service with broader network access (e.g.,
EC2 with a public IP).

### Cross-account data exfiltration via `aws:ResourceAccount`

A policy that grants `s3:GetObject` on `arn:aws:s3:::*/*` allows reading
objects from **any AWS account's buckets**, not just the caller's account,
if the bucket owner cross-accounts the principal. The defense is the
`aws:ResourceAccount` condition:

```json
"Condition": { "StringEquals": { "aws:ResourceAccount": "123456789012" } }
```

Without this condition, any resource wildcard spanning `*` is a
cross-account exfiltration vector. Flag broad S3/KMS/SQS resource patterns
without `aws:ResourceAccount` as **AMBIGUOUS** at minimum.

### Tag-mutation bypass of `aws:ResourceTag` conditions

ABAC policies conditioned on `aws:ResourceTag/Environment: prod` are
**bypassable** if the principal also has `tag:TagResources` (or a broad
permission like `ec2:*` that includes tagging). The principal can tag any
resource with `Environment=prod` and then access it. When evaluating
tag-based conditions, check whether the same policy (or other policies
attached to the principal) grants tagging permissions on the same resource
type. If so, downgrade the classification — the tag condition provides no
real boundary.

### `kms:Decrypt` on `Resource: "*"`

Even without `kms:*`, a grant of `kms:Decrypt` on `"*"` is a silent data
exfiltration vector. If any AWS service uses a customer-managed KMS key for
encryption (S3 server-side encryption, EBS volumes, RDS snapshots, Secrets
Manager), a principal with `kms:Decrypt` on `"*"` can decrypt that data
*if they can first access the ciphertext*. Classify `kms:Decrypt` on `"*"`
as **OVERPERMISSIVE** with **HIGH** risk — it is a data-access multiplier
that silently extends the blast radius of every encrypted resource.

### Condition-key bypass catalog

| Pattern | Exploitation mechanic | Correct defense |
| --- | --- | --- |
| `aws:SourceIp: 0.0.0.0/0` | CIDR covers entire internet; no restriction | Use real egress CIDR or remove condition |
| `ForAllValues:StringEquals` | True when request has zero matching values — absent key bypasses | Use `ForAnyValue` or add explicit Deny on `Null` |
| `Null: { key: "false" }` | Means "key must be absent" — true when MFA never checked | Use `"true"` (require presence) + `Bool` check |
| `StringLike` without anchors | `${aws:username}` in a resource ARN with `StringLike` can match unintended paths if username contains special chars | Use `StringEquals` for exact, or anchor with explicit `*` placement |
| `aws:PrincipalArn` in trust policy | A trust policy granting `sts:AssumeRole` to `aws:PrincipalArn` matching a broad pattern can be exploited by any matching principal | Restrict to exact ARN, never pattern-match on principal |
| `aws:RequestTag` without `ForAllValues` | Only checks tags present in request; does not enforce required tags exist | Pair with `Null` check or `ForAllValues:StringEquals` |
| Missing `aws:SecureTransport` | Allows HTTP alongside HTTPS for API calls supporting both | Add `Bool: { aws:SecureTransport: "true" }` |
| `aws:MultiFactorAuthPresent` via `Bool` alone | `Bool` check fails silently if key absent (e.g., programmatic call never sets MFA key) | Combine `Null: false` (require key present) with `Bool: true` (require MFA value) |

### MFA condition interaction

The correct MFA enforcement pattern requires **two** conditions working
together — a common error is using only one:

1. `Null: { "aws:MultiFactorAuthPresent": "false" }` — ensures the key EXISTS
   in the request (programmatic calls via CLI/SDK without MFA do NOT include
   this key at all, so a `Bool` check alone silently passes).
2. `Bool: { "aws:MultiFactorAuthPresent": "true" }` — ensures the value is
   true (MFA was actually used).

Using only `Bool` is the most common MFA bypass: the condition evaluates to
false (key absent → not true → condition fails → access denied) in many
cases, BUT certain long-lived credentials (e.g., role assumption chains) may
forward the key unexpectedly, and the absence semantics are
account-dependent. Always use both conditions together.

### Service-specific PassRole variants

`iam:PassRole` is not the only action that passes roles to services.
Several services have their own "pass-role" semantics that do NOT require
`iam:PassRole` but achieve a similar effect:

- `states:CreateStateMachine` / `states:UpdateStateMachine` — passes an
  execution role to Step Functions.
- `glue:CreateJob` / `glue:CreateCrawler` — passes a role to Glue.
- `lex:CreateBot` / `lex:UpdateBot` — passes a role to Lex.
- `opsworks:CreateStack` — passes a role to OpsWorks.

If the policy grants `iam:PassRole` on `"*"`, check whether these service
actions are also allowed — they compound the escalation surface because
each service executes under the passed role's identity.

### Cross-account trust policy abuse

A role trust policy (`Resource`-based policy on the IAM role itself) that
uses `aws:PrincipalArn` or `aws:PrincipalAccount` with a wildcard pattern
(e.g., `arn:aws:iam::*:role/*`) allows **any AWS account** to attempt
assumption. The `sts:ExternalId` condition is the standard defense for
cross-account trust:

```json
"Condition": { "StringEquals": { "sts:ExternalId": "<unique-hardcoded-id>" } }
```

Without `sts:ExternalId`, a confused-deputy attack is possible: any
principal matching the trust pattern can assume the role. Flag trust
policies with broad principal patterns and no `sts:ExternalId` as
**OVERPERMISSIVE**.

## Recent AWS features (2024-2026)

- **IAM Access Analyzer unused-access GA (2024):** Access Analyzer's unused-access analysis is now GA, generating findings for unused IAM roles, access keys, passwords, permissions, and SCPs. This directly supports the least-privilege audit — auditors should cross-reference unused-access findings with the IAM policy analysis to identify both over-broad AND unused permissions.
- **Identity Center (SSO) updates (2024-2025):** AWS IAM Identity Center received enhanced permission set management and application assignment features. Auditors should verify that Identity Center permission sets do not include wildcard actions and that application assignments are scoped to necessary principals only.
- **New condition keys (2024-2025):** AWS added new global condition keys including `aws:SourceOrgID`, `aws:SourceOrgPaths`, and enhanced `aws:CalledVia` / `aws:CalledViaFirst` / `aws:CalledViaLast`. Auditors should verify that policies use the strongest available condition key for service-to-service integrations.
- **Session policies and permissions boundaries awareness:** The analysis should account for permissions boundaries and session policies when computing effective permissions — an over-permissive IAM policy may be mitigated by a boundary. However, the absence of a boundary means the IAM policy IS the effective permission.
