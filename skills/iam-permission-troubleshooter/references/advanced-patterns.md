# Advanced Patterns — IAM Permission Troubleshooter

Expert edge cases, Deny-pattern and cross-account catalogs, expert heuristics, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## ARN format gotcha (from SKILL.md § Step 2)

**ARN format gotcha (Step 4 root cause #1).** The single most common IAM
misdiagnosis is "the policy has `s3:GetObject` on the bucket ARN." For S3:

- Bucket-level actions (`s3:ListBucket`, `s3:DeleteBucket`, `s3:GetBucketLocation`) require `arn:aws:s3:::bucket-name` (no `/*`).
- Object-level actions (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`) require `arn:aws:s3:::bucket-name/*` (with `/*`).

Confusing the two produces AccessDenied on a policy that "looks right." A
similar pattern exists for SQS (`arn:aws:sqs:...:queue-name` vs queue URL),
and for Secrets Manager (`arn:aws:secretsmanager:...:secret:name-??????`
with the random 6-char suffix).

## Common Deny patterns (from SKILL.md § Step 4)

**Common Deny patterns to look for first:**

- **Region restriction SCP.** `Condition: { "StringNotEquals": { "aws:RequestedRegion": ["us-east-1", "us-west-2"] } }` — denies anything outside the listed regions. Often deployed org-wide and forgotten when a workload moves regions.
- **IP restriction in identity policy or boundary.** `Condition: { "NotIpAddress": { "aws:SourceIp": ["10.0.0.0/8"] } }` — denies anything outside the corporate CIDR. Breaks when a Lambda runs from a VPC with a NAT gateway whose EIP is not on the allowlist.
- **VPC endpoint restriction.** `Condition: { "StringNotEqualsIfExists": { "aws:sourceVpce": "vpce-aaaaaaa" } }` — denies anything not coming through the specified VPC endpoint. Breaks cross-region or cross-account traffic.
- **MFA requirement.** `Condition: { "Bool": { "aws:MultiFactorAuthPresent": "false" } }` — programmatic calls without MFA fail. Note that long-lived access keys never set the MFA key, so `Bool` evaluates false; the correct pattern is `Null` + `Bool` together.
- **Resource tag requirement.** `Condition: { "StringNotEquals": { "aws:ResourceTag/Environment": "prod" } }` — denies access to resources without the tag. Breaks when a new resource is created without tags.
- **`aws:SourceArn` / `aws:SourceAccount` on a service-to-service chain.** A KMS key policy that requires `aws:SourceAccount: "111111111111"` denies a cross-account S3 access because the KMS call is made by S3 on behalf of the caller — the `aws:SourceAccount` is the S3 service account, not the caller's.

**NotAction in a Deny is the easiest to miss.** A Deny statement with
`NotAction: ["iam:*"]` denies every action except `iam:*`. Operators read
"iam:*" and think the statement is about IAM; it is actually denying
everything else. Scan all Deny statements for `NotAction` / `NotResource`
first — they are the broadest denies.

## Common cross-account failures (from SKILL.md § Step 7)

Common cross-account failures:

1. **S3 bucket policy missing the cross-account principal.** A Lambda in
   account B reading an object in account A's bucket needs the bucket
   policy in A to list B's role ARN in `Principal`. Adding the IAM
   permission to B's Lambda role is necessary but not sufficient.
2. **KMS key policy does not grant decrypt to the cross-account caller.**
   Even if the S3 bucket policy allows B to read the object, if the
   object is encrypted with a KMS key in account A, the key policy must
   also grant `kms:Decrypt` to B's role. This is a three-party chain
   (Lambda role → S3 → KMS) that fails at KMS even though S3 works.
3. **SQS queue policy does not grant `sqs:SendMessage` cross-account.**
   Same pattern as S3.
4. **Secrets Manager secret policy missing the cross-account principal.**
   Same pattern; additionally, the KMS key used to encrypt the secret
   must also grant decrypt to the caller.
5. **Cross-account Lambda invocation.** `lambda:InvokeFunction`
   resource-based policy on the function must list the cross-account
   caller. The caller's identity policy must also Allow `lambda:InvokeFunction`.

For any cross-account failure, output both sides in the EVIDENCE block:
"Caller identity policy: <Allowed / Denied / Missing action>. Target
resource-based policy: <Allowed / Denied / Missing principal>."

## Expert edge cases (from SKILL.md § Expert edge cases)

### The `aws:SourceAccount` chain on service-to-service calls

When S3 reads an object encrypted with a KMS key, the KMS `Decrypt` call
is made BY S3 on behalf of the calling principal — not by the principal
directly. A KMS key policy that requires `aws:SourceAccount: "111111111111"`
expects the source account of the S3 service call to be `111111111111`,
but if the bucket is in `222222222222`, the S3 service call originates
from `222222222222`, not the caller's account. The key policy denies
the call even though the principal appears in the policy. Fix: scope on
`aws:SourceArn` of the bucket instead, OR list the bucket's account in
`aws:SourceAccount`.

### The VPC endpoint policy shadow

A VPC endpoint has its own policy that is independent of IAM. If a VPC
endpoint policy denies an action, the request fails even though every
IAM policy allows it. The CloudTrail event will show AccessDenied with
no hint that the VPC endpoint policy is the cause. The diagnostic is to
bypass the endpoint (route over the internet or a different endpoint)
and see if the call succeeds. VPC endpoint policies are the most
overlooked layer because they live in the VPC console, not IAM.

### Session policies injected by federation

When a user federates via IAM Identity Center or a SAML provider, the
federation flow can inject a session policy that narrows the role's
effective permissions. The session policy is NOT visible in the role's
policy list — it lives in the `assumeRole` request parameters. A common
failure: a SAML claim maps to a session policy that includes a
`Resource: "arn:aws:s3:::personal-${aws:username}/*"` restriction, and
the username has special characters that cause the substitution to fail
silently. The CloudTrail `userIdentity.sessionContext.sessionIssuer`
field reveals the session policy presence.

### The CloudFormation service-linked role pass-through

When CloudFormation creates a stack, it makes calls under its own
service-linked role (`AWSServiceRoleForCloudFormation`) for some
operations and under the passed role for others. A caller with
`cloudformation:CreateStack` but without `iam:PassRole` on the stack's
execution role gets `AccessDenied` on CreateStack even though the policy
allows CreateStack — CloudFormation needs PassRole to receive the
execution role. The error message rarely mentions PassRole. The fix is
to add `iam:PassRole` on the specific execution role ARN with
`iam:PassedToService: cloudformation.amazonaws.com`.

### Condition-key mismatch on `aws:ResourceTag`

Tag-based conditions are case-sensitive. A policy conditioned on
`aws:ResourceTag/Environment: prod` does NOT match a tag `environment:
prod` (lowercase key). AWS normalises tag VALUES to lowercase for some
services but not tag KEYS. The diagnostic is to read the actual tag key
case from `aws <service> describe-tags` output, not from the policy.

### The `StringLike` wildcard anchor trap

A trust policy with
`"StringLike": { "sts:RoleName": "dev-*" }` matches `dev-app` AND
`development-app` AND `devops-app`. Operators intend "starts with dev-"
but the wildcard matches anywhere. The fix is to anchor explicitly:
`dev-*` is correct only if the role names always start with `dev-`. For
service-role patterns, prefer `StringEquals` on a full role-name list
over `StringLike` patterns.

### Resource-based policy principal format

For Lambda function policies, the `Principal` MUST be a service principal
(`lambda.amazonaws.com`), an account root (`111111111111`), or an IAM
ARN. SAML/OIDC federation principals are NOT supported in Lambda function
policies — they must assume an IAM role first. A common failure is to
try granting a SAML principal direct access to a Lambda function via the
function policy.

### IAM database authentication quasi-policy

RDS IAM authentication uses a special quasi-policy mechanism. The caller
needs `connect:DB` on the DB cluster ARN — NOT `rds-db:connect`. The
action prefix changed in 2018 but old documentation still references
`rds-db:connect`. The error is AccessDenied on a policy that has the
wrong action name.

## Recent AWS features (2024-2026)

- **Access Analyzer policy validation (2024 GA):** Access Analyzer now
  surfaces logical errors, unused actions, and notable findings directly
  in the IAM console. For troubleshooting, generate a policy from
  CloudTrail activity via Access Analyzer to see what the principal
  actually does — the generated policy is the authoritative scope.
- **IAM Identity Center (SSO) permission sets and session policies
  (2024-2025):** Identity Center can inject session policies via
  permission set associations. Troubleshoot SSO-routed AccessDenied by
  reading the permission set's inline policy AND the session policy
  that Identity Center attaches.
- **`aws:CalledVia` / `aws:CalledViaFirst` / `aws:CalledViaLast` (2024):**
  These condition keys identify service-chain calls. Use them to scope
  Deny statements that should apply only when a call is made through a
  specific service (e.g., deny direct S3 access but allow S3 access via
  CloudFormation).
- **`aws:SourceOrgID` / `aws:SourceOrgPaths` (2024-2025):** For
  organizations-wide trust policies, these keys are more stable than
  `aws:SourceAccount` because they survive account moves between OUs.
- **Cross-account S3 access with bucket-owner-enforced ACLs (2024):**
  The default S3 ACL model now uses bucket-owner-enforced ACLs. Cross-
  account uploads work differently — the bucket owner automatically owns
  the object. This changes which KMS key policy entries are required for
  encrypted cross-account writes.

## Expert heuristic: the works-for-admin-but-not-for-me pattern

When the root user or an administrator with `Action: "*", Resource: "*"`
can perform an operation but a specific IAM identity cannot, the cause
is almost always in the IAM identity's own policy stack — not the
resource or the service. Root and admin effective permissions are the
union of `*`, so any deny must live below them in the evaluation chain
(identity-based, boundary, session, or an SCP that explicitly Denies).

**Diagnostic shortcut — simulate the identity directly:**

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <user-or-role-arn> \
  --action-names <denied-action> \
  --resource-arns <target-arn> \
  --eval-decision SHAPE \
  --output json
```

The simulator walks identity-based + boundary + session policies
together and returns `allowed`, `implicitDeny`, or `explicitDeny`. If
the admin simulator returns `allowed` but the identity returns
`implicitDeny`, the missing statement is in the identity-based or
boundary layer. If `explicitDeny`, hunt for the Deny statement in the
identity-based or boundary policy — a session policy cannot Deny.

**Common root causes for this pattern:**
1. Identity-based policy missing the specific action or resource ARN.
2. Permissions boundary attached but not granting the action.
3. SCP at the OU or account level (SCPs still apply to admins only if
   they explicitly Deny — an explicit-Deny SCP blocks admins too).
4. Session policy injected by federation scoping the role down.

## Edge case: STS session policy scoping

When a principal assumes a role via `sts:AssumeRole` with a session
policy (`--policy-arns` or `--policy`), the session's effective
permissions are the INTERSECTION of the role's identity-based policy
AND the session policy:

```
effective = role_policy ∩ session_policy
```

A session policy can only NARROW permissions — never widen. The most
common failure pattern: a CI/CD system assumes a deployment role and
injects a session policy scoping the session to a single S3 prefix; a
later pipeline step that writes to a different prefix fails with
AccessDenied even though the role's identity-based policy Allows it.

**Diagnosis:**
- CloudTrail `userIdentity.sessionContext.sessionIssuer` reveals the
  session policy presence.
- The session policy itself is NOT visible in the role's policy list —
  it lives in the assume-role request parameters.
- Re-run `sts:AssumeRole` without `--policy-arns` to confirm the role
  policy alone is sufficient.

**Fix:** widen the session policy (not the role policy) to include the
additional prefix, OR drop the session policy if the role's identity-
based policy is already correctly scoped.
