# IAM Permission Gotchas — Catalog

Supplementary reference for the IAM Permission Troubleshooter skill. 30+
real-world AccessDenied patterns and their fixes, organised by category.

## ARN format gotchas

### 1. S3 bucket vs object ARN

**Symptom:** Policy has `s3:GetObject` on `arn:aws:s3:::my-bucket`.
AccessDenied.

**Cause:** Object-level actions require `arn:aws:s3:::my-bucket/*` (with
`/*` suffix). The bucket ARN matches only bucket-level actions like
`s3:ListBucket`.

**Fix:** Add the `/*` suffix:

```json
"Resource": [
  "arn:aws:s3:::my-bucket",
  "arn:aws:s3:::my-bucket/*"
]
```

### 2. Secrets Manager secret ARN with random suffix

**Symptom:** Policy references
`arn:aws:secretsmanager:us-east-1:111111111111:secret:my-secret`. Works
once, fails after rotation.

**Cause:** Secrets Manager ARNs include a 6-character random suffix
(`-ABCDEF`) that changes when the secret is rotated. A policy pinning
the exact ARN breaks on the next rotation.

**Fix:** Use a wildcard:

```json
"Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:my-secret-*"
```

### 3. SQS queue ARN vs URL

**Symptom:** Policy references the queue URL
(`https://sqs.us-east-1.amazonaws.com/...`) instead of the ARN.

**Cause:** IAM policies use the ARN format (`arn:aws:sqs:us-east-1:...:queue-name`),
NOT the URL. The SDK accepts the URL for API calls; IAM rejects it.

**Fix:** Use the ARN format.

### 4. IAM role path

**Symptom:** Policy references
`arn:aws:iam::111111111111:role/MyRole` but the role was created with a
path (`/service/MyRole`).

**Cause:** IAM role ARNs include the path. The full ARN is
`arn:aws:iam::111111111111:role/service/MyRole`.

**Fix:** Use `aws iam get-role --role-name MyRole` to retrieve the
exact ARN including path.

## Condition key gotchas

### 5. `aws:SourceIp` for VPC workloads

**Symptom:** Policy has `aws:SourceIp: 10.0.0.0/8`. Lambda in a VPC
fails with AccessDenied. Same role works from corporate network.

**Cause:** Lambda in a VPC egresses through a NAT gateway whose EIP is
the source IP from AWS's perspective. The NAT EIP is not in `10.0.0.0/8`.

**Fix:** Use `aws:SourceVpc` or `aws:SourceVpce` instead, OR add the
NAT EIP CIDR to the condition.

### 6. `aws:RequestedRegion` SCP overreach

**Symptom:** A workload deployed in `eu-west-1` fails after the security
team deploys an SCP restricting to `us-east-1, us-west-2`.

**Cause:** SCP with `StringNotEquals: aws:RequestedRegion: ["us-east-1",
"us-west-2"]` denies anything outside those regions.

**Fix:** Add the workload's region to the SCP allowlist. If the SCP is
owned by a central team, ESCALATE.

### 7. MFA condition using only `Bool`

**Symptom:** Policy has `Bool: aws:MultiFactorAuthPresent: true`. CLI
calls fail even when MFA is configured.

**Cause:** Long-lived access keys never set the MFA key. `Bool` evaluates
to false (key absent → not true → deny). The correct pattern requires
BOTH `Null: false` (key present) AND `Bool: true` (value true).

**Fix:**

```json
"Condition": {
  "Null": { "aws:MultiFactorAuthPresent": "false" },
  "Bool": { "aws:MultiFactorAuthPresent": "true" }
}
```

### 8. `ForAllValues:StringEquals` absent-key bypass

**Symptom:** Policy with `ForAllValues:StringEquals: aws:RequestedRegion:
us-east-1` allows requests that should be denied.

**Cause:** `ForAllValues` returns true when the request has zero matching
values — i.e., when the key is absent. A request that does not set
`aws:RequestedRegion` bypasses the condition.

**Fix:** Use an explicit Deny with `Null` check:

```json
{
  "Effect": "Deny",
  "Action": "*",
  "Resource": "*",
  "Condition": {
    "Null": { "aws:RequestedRegion": "false" },
    "StringNotEquals": { "aws:RequestedRegion": ["us-east-1"] }
  }
}
```

### 9. Tag key case sensitivity

**Symptom:** Policy with `aws:ResourceTag/Environment: prod`. Resources
tagged with lowercase `environment: prod` get AccessDenied.

**Cause:** Tag KEY names are case-sensitive. `Environment` and
`environment` are different keys.

**Fix:** Standardise tag key case in the account. Use AWS Config rules
or tag policies to enforce consistency.

### 10. `StringLike` wildcard anchor trap

**Symptom:** Trust policy with `StringLike: sts:RoleName: "dev-*"` allows
roles named `development-app` and `devops-app`.

**Cause:** `*` matches anywhere in the string. `dev-*` is not anchored
to the start.

**Fix:** Use `StringEquals` with an explicit list, OR document the
intended match pattern and verify role names against it.

## Cross-account gotchas

### 11. KMS key policy on encrypted S3 object

**Symptom:** Cross-account Lambda reads S3 object. `s3:GetObject` works
on plaintext objects, fails on encrypted objects.

**Cause:** KMS Decrypt call is made by S3 on behalf of the caller. Key
policy in the resource-owning account does not grant `kms:Decrypt` to
the cross-account caller.

**Fix:** Add the caller role ARN to the KMS key policy. See
`policy-evaluation-logic.md` for the worked example.

### 12. S3 bucket policy principal format

**Symptom:** Bucket policy grants access to
`arn:aws:iam::111111111111:root` but Lambda in 111111111111 still gets
AccessDenied.

**Cause:** `root` principal delegates to the account's identity-based
policy. If the Lambda role's identity policy does not also Allow
`s3:GetObject`, the cross-account intersection fails.

**Fix:** Either add `s3:GetObject` to the Lambda role identity policy
(preferred), OR change the bucket policy `Principal` to the specific
Lambda role ARN (skips identity-policy requirement).

### 13. Lambda function policy for cross-account invoke

**Symptom:** Account A's Lambda calling `lambda:InvokeFunction` on
account B's function. AccessDenied.

**Cause:** Lambda function resource-based policy does not list account A
caller.

**Fix:** Add a statement to the function's resource-based policy:

```bash
aws lambda add-permission \
  --function-name <function> \
  --statement-id CrossAccountInvoke \
  --action lambda:InvokeFunction \
  --principal 111111111111
```

### 14. SQS cross-account SendMessage

**Symptom:** Cross-account producer cannot send to SQS queue.

**Cause:** Queue policy does not grant `sqs:SendMessage` cross-account.

**Fix:** Add the producer account to the queue policy `Principal`.

### 15. Secrets Manager cross-account with KMS

**Symptom:** Cross-account principal can read the secret metadata but
not the secret value.

**Cause:** Secret policy allows cross-account, but the KMS key used to
encrypt the secret does not. Secrets Manager decrypts the value using
KMS — the key policy must also grant `kms:Decrypt` to the cross-account
caller.

**Fix:** Update BOTH the secret resource policy AND the KMS key policy.

## Service-linked role gotchas

### 16. Trusted Advisor / Support missing service-linked role

**Symptom:** Trusted Advisor returns no results.

**Cause:** `AWSServiceRoleForSupport` missing from the account.

**Fix:**

```bash
aws iam create-service-linked-role --aws-service-name support.amazonaws.com
```

### 17. Organization account move leaves orphaned service-linked roles

**Symptom:** After moving an account between OUs, some services fail.

**Cause:** Service-linked roles are account-local. Moving accounts does
not move roles. The new account may not have the required SLR.

**Fix:** Create the missing service-linked role in the moved account.

## PassRole gotchas

### 18. EC2 launch with instance profile

**Symptom:** `Client.UnauthorizedOperation` on `ec2:RunInstances` even
though `ec2:RunInstances` is in the policy.

**Cause:** Caller lacks `iam:PassRole` on the instance profile's role
ARN. EC2 needs to receive the role.

**Fix:** Add `iam:PassRole` on the specific role ARN:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::111111111111:role/ec2-instance-profile",
  "Condition": {
    "StringEquals": { "iam:PassedToService": "ec2.amazonaws.com" }
  }
}
```

### 19. Lambda creation with execution role

**Symptom:** `AccessDenied` on `lambda:CreateFunction` even though
`lambda:CreateFunction` is in the policy.

**Cause:** Caller lacks `iam:PassRole` on the Lambda execution role ARN.

**Fix:** Add `iam:PassRole` on the specific role ARN with
`iam:PassedToService: lambda.amazonaws.com`.

### 20. CloudFormation stack creation

**Symptom:** `AccessDenied` on `cloudformation:CreateStack` even with
the action in the policy.

**Cause:** CloudFormation needs `iam:PassRole` on the stack's execution
role. The error message rarely mentions PassRole.

**Fix:** Add `iam:PassRole` on the specific role ARN with
`iam:PassedToService: cloudformation.amazonaws.com`.

## SCP / boundary gotchas

### 21. Region restriction SCP

**Symptom:** Workload deployed in `ap-southeast-2` fails. Same workload
works in `us-east-1`.

**Cause:** SCP with `aws:RequestedRegion` restriction deployed at root
or production OU.

**Fix:** Add `ap-southeast-2` to the SCP allowlist. ESCALATE if the SCP
is centrally owned.

### 22. Permissions boundary caps scope

**Symptom:** Identity policy Allows `s3:*` on `*` but Lambda cannot
write to a new bucket.

**Cause:** Permissions boundary on the role restricts to specific
buckets. Identity policy is wider than the boundary.

**Fix:** Add the new bucket to the permissions boundary. Boundaries cap
maximum effective permissions.

### 23. VPC endpoint policy shadow

**Symptom:** DynamoDB access fails from inside a VPC. Same role works
from outside the VPC.

**Cause:** VPC endpoint policy for `com.amazonaws.<region>.dynamodb`
restricts to specific table ARNs.

**Fix:** Update the VPC endpoint policy to include the new table.

## Federation / session policy gotchas

### 24. SAML attribute to session policy mapping

**Symptom:** Identity Center user has AccessDenied to S3 buckets that
the permission set's inline policy allows.

**Cause:** A SAML claim maps to a session policy that narrows scope to
`personal-${aws:username}/*`. The user's username has uppercase letters
that S3 normalises differently.

**Fix:** Standardise username case, OR use a different attribute for the
session policy mapping.

### 25. Cross-org AssumeRole after org change

**Symptom:** AssumeRole fails after an account moves between
Organizations.

**Cause:** Trust policy uses `aws:PrincipalOrgID` condition. The moved
account has a new OrgID.

**Fix:** Update the trust policy OrgID, OR move the account back into
the original org.

### 26. Session policy cannot widen scope

**Symptom:** Operator passes a session policy at assume-role time to
grant additional permissions. AssumeRole succeeds but the additional
permissions are not effective.

**Cause:** Session policies can only NARROW the role's effective
permissions. They cannot grant beyond the role's policy.

**Fix:** Update the role's identity-based policy to include the
additional permissions.

## Service-specific gotchas

### 27. RDS IAM authentication action name

**Symptom:** RDS IAM auth fails with AccessDenied. Policy has
`rds-db:connect`.

**Cause:** The action prefix changed in 2018. The correct action is
`connect:DB` on the DB cluster ARN.

**Fix:** Update the policy to use `connect:DB`.

### 28. ECR image pull requires multiple actions

**Symptom:** ECS task cannot pull ECR image. Policy has
`ecr:GetDownloadUrlForLayer`.

**Cause:** ECR pull requires FOUR actions: `ecr:BatchCheckLayerAvailability`,
`ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, and
`ecr:GetAuthorizationToken`. Missing any one fails.

**Fix:** Add all four actions. Use the managed policy
`AmazonEC2ContainerRegistryReadOnly`.

### 29. CloudWatch Logs requires CreateLogStream + PutLogEvents

**Symptom:** Lambda cannot write logs. Policy has `logs:CreateLogGroup`.

**Cause:** Lambda needs `logs:CreateLogStream` AND `logs:PutLogEvents`
on the log stream ARN. `CreateLogGroup` is only needed once.

**Fix:** Use the managed policy `AWSLambdaBasicExecutionRole`.

### 30. S3 pre-signed URL does not bypass IAM

**Symptom:** Operator generates a pre-signed URL for a cross-account
principal. Principal uses the URL, gets AccessDenied.

**Cause:** Pre-signed URLs authenticate the SIGNER, not the caller. The
signer must have `s3:GetObject` on the object. The caller does not need
IAM permissions — they use the URL.

**Fix:** Verify the signer's role has `s3:GetObject`. If the signer is
a Lambda, the Lambda's execution role needs the permission.

## Diagnostic tips

- **Always run `aws sts get-caller-identity` first.** It reveals whether
  the caller is an assumed role, federated principal, or root. Federation
  paths carry session policies.
- **Use `--dry-run` on EC2 calls.** It surfaces the exact missing
  permission without making the call.
- **Cross-reference simulator output with CloudTrail.** The simulator
  tests individual actions; chained flows need CloudTrail evidence.
- **For assumed-role failures, read the TARGET role's trust policy
  first.** The caller-side identity policy is rarely the issue for
  AssumeRole.
- **For cross-account failures, write out BOTH sides of the policy
  before declaring the root cause.** The intersection rule is
  non-negotiable.
