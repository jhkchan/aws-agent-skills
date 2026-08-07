# IAM Policy Evaluation Logic — Reference

Supplementary reference for the IAM Permission Troubleshooter skill.
Walks the full evaluation order with worked examples per layer.

## Evaluation order (canonical)

AWS evaluates a request through up to six independent layers. The first
layer to return an explicit `Deny` wins. Otherwise, every required layer
must return an `Allow`. The order below is fixed.

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Organisation SCPs                                          │
│     - Evaluated top-down: root → parent OUs → account          │
│     - At each level: explicit Deny wins; otherwise must Allow  │
│     - SCPs NEVER grant — they only restrict (max allowed scope)│
├─────────────────────────────────────────────────────────────────┤
│  2. Resource-based policy (on the target resource)             │
│     - S3 bucket, KMS key, SQS, Secrets Manager, Lambda fn      │
│     - Same-account:  identity  ∪  resource  (union — EITHER)   │
│     - Cross-account: identity  ∩  resource  (intersection)     │
├─────────────────────────────────────────────────────────────────┤
│  3. Identity-based policy (managed + inline on the principal)  │
│     - The most visible layer — first place operators look      │
│     - Often NOT the cause when SCPs / boundaries exist         │
├─────────────────────────────────────────────────────────────────┤
│  4. Permissions boundary (if attached to the role)             │
│     - Caps the maximum effective permissions                   │
│     - Identity policy Allows + boundary Denies = DENY          │
├─────────────────────────────────────────────────────────────────┤
│  5. Session policy (if assumed role with session policy)       │
│     - Effective permissions = role policy ∩ session policy     │
│     - Injected by federation (SAML, OIDC) or API callers       │
├─────────────────────────────────────────────────────────────────┤
│  6. VPC endpoint policy + service-specific controls            │
│     - VPC endpoint policy is independent of IAM                │
│     - Some services have secondary controls (e.g., KMS grants) │
└─────────────────────────────────────────────────────────────────┘
```

**Explicit Deny wins everywhere.** A Deny in ANY of the six layers is
final. Adding Allows in other layers does not help. This is why the
diagnostic walk must check every layer — the operator's instinct is to
keep adding Allows to the identity-based policy, which is futile if the
real deny lives in an SCP or boundary.

## Layer 1: Organisation SCPs

SCPs live in the Organizations management account (or a delegated
administrator). They are evaluated top-down through the OU hierarchy.

```
Root SCP  ──>  OU-level SCP  ─>  OU-level SCP  ─>  Account-level SCP
```

At each level:

- An explicit `Deny` blocks the request, regardless of lower levels.
- An `Allow` does NOT grant access — it just lets the next level evaluate.
- If no `Allow` exists at any level for the action, the request is
  implicitly denied at the account level.

**Common SCP denies:**

- `aws:RequestedRegion` restriction — denies anything outside the listed
  regions. Frequently deployed at the root or a "production" OU.
- Service deny lists — denies `iam:*`, `kms:*`, etc. for developer
  accounts.
- `aws:SourceIp` corporate CIDR restriction.
- Resource tag requirement (`aws:ResourceTag/Environment: prod`).

**Diagnostic command:**

```bash
aws organizations list-policies-for-target \
  --target-id <account-id> \
  --filter SERVICE_CONTROL_POLICY
aws organizations describe-policy --policy-id <p-xxxxxxxx>
```

If the operator has no access to the management account, output
ESCALATE — SCP issues cannot be resolved from the member account.

## Layer 2: Resource-based policy

Resource-based policies are attached to the resource (S3 bucket, KMS
key, SQS queue, Secrets Manager secret, Lambda function, etc.). They
are evaluated independently of the caller's identity-based policy.

### Same-account (union rule)

For same-account access, EITHER the identity-based OR the resource-based
policy can grant access. A principal with no identity-based Allow can
still access a resource if the resource-based policy lists them in
`Principal`.

### Cross-account (intersection rule)

For cross-account access, BOTH the identity-based AND the resource-based
policy must Allow. This is non-negotiable.

```
Same-account:   identity  ∪  resource  → allowed if EITHER Allows
Cross-account:  identity  ∩  resource  → allowed only if BOTH Allow
```

**Worked example — cross-account S3 read.**

Caller: `arn:aws:iam::111111111111:role/app-lambda` (account 111)
Target: `arn:aws:s3:::data-bucket/file.txt` (account 222)

Required:
1. Account 111 Lambda role identity policy: `s3:GetObject` on
   `arn:aws:s3:::data-bucket/*`.
2. Account 222 bucket policy: `Principal: { AWS: arn:aws:iam::111111111111:role/app-lambda }`,
   `Action: s3:GetObject`, `Resource: arn:aws:s3:::data-bucket/*`.

If EITHER is missing, AccessDenied.

**Worked example — KMS decrypt on encrypted S3 object.**

Three layers of policy must align:

1. S3 bucket policy (in object-owning account) — grants `s3:GetObject`
   to the caller role.
2. Caller's identity policy — grants `s3:GetObject` on the bucket ARN
   AND `kms:Decrypt` on the key ARN.
3. KMS key policy (in key-owning account) — grants `kms:Decrypt` to the
   caller role.

The KMS Decrypt call is made BY S3 on behalf of the caller — the key
policy must include the caller role in `Principal`, and may require
`aws:SourceAccount` or `aws:SourceArn` conditions to scope the chain.

## Layer 3: Identity-based policy

The most visible layer. Sum of all managed and inline policies attached
to the principal.

**Evaluation:**

1. Combine all Allow statements across managed + inline.
2. Combine all Deny statements across managed + inline.
3. Explicit Deny wins.
4. If no Allow matches the action+resource+condition: implicit deny.

**Common failures:**

- Missing action (e.g., policy has `s3:PutObject` but not `s3:GetObject`).
- Wrong resource ARN shape (e.g., `s3:GetObject` on bucket ARN without
  `/*`).
- Condition not satisfied (e.g., `aws:SourceIp` not matching NAT EIP).
- `NotAction` interpreted as "action list" instead of "everything but."

## Layer 4: Permissions boundary

A permissions boundary is a separate managed policy attached to a role
that CAPS the maximum effective permissions. Identity-based policy +
boundary = intersection.

```
Effective = Identity-based Allow ∩ Boundary Allow
```

If identity policy Allows `s3:*` but boundary only Allows `s3:GetObject`,
the effective permission is `s3:GetObject` only.

**Diagnostic:**

```bash
aws iam get-role --role-name <role> --query 'Role.PermissionsBoundary'
```

If `PermissionsBoundary` is non-null, the boundary MUST also Allow the
action. Boundaries are often attached by central security teams and
forgotten by application teams.

## Layer 5: Session policy

A session policy is passed at assume-role time (or injected by Identity
Center federation). It can only NARROW the role's effective permissions.

```
Effective = Role policy ∩ Session policy
```

Session policies are NOT visible in the role's policy list. They live
in the `assumeRole` call parameters. CloudTrail `userIdentity.sessionContext`
reveals their presence.

**Worked example — Identity Center session policy.**

Identity Center permission sets can attach a session policy that scopes
access per user. A permission set with a session policy
`{ "Statement": [{ "Effect": "Allow", "Action": "s3:*", "Resource": "arn:aws:s3:::personal-${aws:username}/*" }] }`
restricts every role assumed through Identity Center to the user's
personal S3 prefix.

If the username contains characters that break the path (e.g., uppercase
that S3 normalises differently than IAM), the substitution can produce
a non-matching ARN, causing AccessDenied on resources the operator
believes should be in scope.

## Layer 6: VPC endpoint policy and service-specific controls

VPC endpoints have their own policy layer, independent of IAM. A VPC
endpoint policy that denies an action blocks the request even if every
IAM policy allows it.

**Common failure:**

A DynamoDB VPC endpoint policy that allows only specific tables blocks
access to other tables, even though the IAM role has `dynamodb:*` on
`*`. The error is AccessDenied with no IAM-side explanation.

**Diagnostic:**

```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids <vpce-xxxx>
# Read the policy document in the output.
```

**Bypass test:** route the request over the public internet (or a
different endpoint) to see if the call succeeds. If yes, the VPC
endpoint policy is the cause.

## Cross-account decision matrix

| Caller location | Resource location | Identity policy | Resource policy | Result |
|---|---|---|---|---|
| Same account | Same account | Allow | (none) | Allow |
| Same account | Same account | (none) | Allow | Allow (union) |
| Same account | Same account | Allow | Deny | Deny |
| Account A | Account B | Allow | Allow | Allow |
| Account A | Account B | Allow | (none) | Deny — needs both |
| Account A | Account B | (none) | Allow | Deny — needs both |
| Account A | Account B | Allow | Deny | Deny |

## Common decision-tree shortcuts

- If the symptom is `Client.UnauthorizedOperation` (EC2), start at the
  identity-based policy — EC2 almost always means identity missing.
- If the symptom is `NotAuthorized to perform sts:AssumeRole`, start at
  the TRUST POLICY (resource-based) on the target role — caller-side
  identity is rarely the issue.
- If the call works from the CLI but fails from a service (Lambda, ECS,
  CloudFormation), suspect a service-to-service condition key
  (`aws:SourceArn`, `aws:SourceAccount`, `aws:CalledVia`).
- If the call works in region A but fails in region B, suspect an SCP
  with `aws:RequestedRegion`.
- If the call works for one principal but not another in the same
  account, suspect a permissions boundary or session policy difference.
- If the call worked yesterday and fails today, check for a recent SCP
  deployment, KMS key policy rotation, or VPC endpoint policy change.

## Worked example — full walk

**Symptom:** Lambda in account 111 calling `s3:GetObject` on
`arn:aws:s3:::prod-data/report.csv` in account 222 fails with
`AccessDenied`. The bucket is encrypted with a KMS key in account 222.

**Walk:**

1. **SCP (Layer 1):** No SCPs on account 111 or 222 block S3 or KMS.
   Verified via `organizations list-policies-for-target`.
2. **Resource-based (Layer 2):** Bucket policy in account 222 includes
   the Lambda role ARN in `Principal`. Bucket policy OK.
3. **Identity-based (Layer 3):** Lambda role in account 111 has
   `s3:GetObject` on `arn:aws:s3:::prod-data/*` AND `kms:Decrypt` on
   `arn:aws:kms:us-east-1:222222222222:key/abc`. Identity OK.
4. **Boundary (Layer 4):** Lambda role has no boundary. Skip.
5. **Session policy (Layer 5):** Lambda assumed without session policy.
   Skip.
6. **KMS key policy (Layer 2 for KMS):** Key policy in account 222 lists
   account-222 roles only. The cross-account Lambda role is NOT in the
   key policy. **DENY — implicit.**

**Root cause:** KMS key policy missing cross-account grant (catalog #7).

**Fix:**

Add to the KMS key policy in account 222:

```json
{
  "Sid": "AllowDecryptCrossAccount",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111111111111:role/app-lambda" },
  "Action": "kms:Decrypt",
  "Resource": "*"
}
```

The Lambda's identity policy already has `kms:Decrypt` on the key ARN,
so the cross-account intersection is satisfied once the key policy is
updated.

**Verify:**

```bash
aws kms simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/app-lambda \
  --action-names kms:Decrypt \
  --resource-arns arn:aws:kms:us-east-1:222222222222:key/abc
# Expected: allowed
```
