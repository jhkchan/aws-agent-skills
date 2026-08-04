# IAM Policy Analysis Reference Guide

Supplementary reference for the IAM Least-Privilege Advisor skill.

## Wildcard action patterns

| Pattern | Example | Risk | Notes |
| --- | --- | --- | --- |
| `Action: "*"` | All actions | CRITICAL — admin equivalent | Maximum blast radius; equivalent to `AdministratorAccess` |
| Service wildcard | `s3:*`, `ec2:*` | HIGH — all operations in a service | Includes destructive actions (Delete*, Put*, Create*) |
| Privilege-escalation service wildcard | `iam:*`, `sts:*`, `kms:*` | CRITICAL — can create/assume new permissions | Enables privesc beyond the policy itself |
| Read wildcard | `s3:Get*`, `s3:List*` | MODERATE — broad read access | Silently expands as AWS adds new APIs |
| List wildcard | `iam:List*` | MODERATE — enumeration/recon | Useful for attackers mapping the account |
| `NotAction` | Everything except listed | HIGH — inverse wildcard | New APIs auto-included; almost always a misconfiguration |
| `NotResource` | All resources except listed | HIGH — inverse wildcard | Same risk as NotAction but on the resource axis |

## Privilege-escalation action taxonomy

These specific named actions enable a principal to escalate beyond their
own permissions when granted on `Resource: "*"`:

| Action | Escalation Path |
| --- | --- |
| `iam:PassRole` | Pass any role to EC2/Lambda/CloudFormation — the service then acts with that role's permissions |
| `sts:AssumeRole` | Assume any role in the account (or cross-account if trust allows) |
| `iam:CreatePolicy` / `iam:CreatePolicyVersion` | Create arbitrary permission documents and attach them |
| `iam:AttachRolePolicy` | Attach any managed policy to any role |
| `iam:PutRolePolicy` | Inject an inline policy into any role |
| `iam:UpdateAssumeRolePolicy` | Modify any role's trust policy to allow arbitrary principals |

**Detection rule:** if any of these actions appear with `Resource: "*"` (or
a broad wildcard like `arn:aws:iam::*:role/*`), the policy is
OVERPERMISSIVE even though neither `Action` nor `Resource` is `"*"`.

## Condition key bypass reference

| Pattern | Why It Bypasses | Fix |
| --- | --- | --- |
| `aws:SourceIp: 0.0.0.0/0` | CIDR covers the entire internet | Remove the condition or use the real egress CIDR |
| `ForAllValues:StringEquals` | True when request has zero matching values | Use `ForAnyValue` or add an explicit deny on absence |
| `Null: { key: "false" }` | Means "key must be absent" — true when key never set | Use `"true"` to require presence, then add a `Bool` check |
| `StringEquals` without `StringEqualsIgnoreCase` | Case mismatch silently fails | Use case-insensitive variant for human-provided values |
| Missing `aws:SecureTransport` | Allows HTTP (port 80) alongside HTTPS | Add `Bool: { aws:SecureTransport: "true" }` |

## Resource patterns

| Pattern | Example | Scope |
| --- | --- | --- |
| `Resource: "*"` | All resources in the account | No scope restriction — dangerous with any wildcard action |
| Partition wildcard | `arn:aws-*:s3:::bucket` | Spans commercial, GovCloud, and China partitions |
| Global S3 scope | `arn:aws:s3:::*` | Every S3 bucket globally, not just account buckets |
| ARN with wildcard | `arn:aws:s3:::app-data-*` | Scoped to a naming prefix — acceptable |
| Specific ARN | `arn:aws:s3:::app-data-prod` | Tightly scoped — preferred |

## Legitimate Resource: "*" exceptions

These actions only support `Resource: "*"` by AWS design. They are safe in
a LEAST_PRIVILEGE policy as long as the action is explicitly named:

- `s3:ListAllMyBuckets`, `s3:HeadBucket`
- `iam:ListRoles`, `iam:ListUsers`, `iam:GetAccountSummary`,
  `iam:GetAccountPasswordPolicy`
- `ec2:Describe*` (all describe operations)
- `organizations:DescribeOrganization`, `organizations:ListAccounts`,
  `organizations:ListRoots`
- `cloudwatch:GetMetricStatistics`, `cloudwatch:ListMetrics`
- `logs:DescribeLogGroups`, `logs:DescribeMetricFilters`
- `sts:GetCallerIdentity`, `sts:GetSessionToken`

## Common over-permissive patterns found in the wild

1. **AdministratorAccess managed policy** on an EC2 instance role "just in
   case" — grants every action on every resource.

2. `s3:*` on `*` used by a Lambda that only reads objects — should be
   `s3:GetObject` on the specific bucket ARN.

3. `iam:PassRole` on `*` — allows passing any role to any service. The
   most common privilege-escalation vector in production IAM.

4. `NotAction: ["iam:*"]` with `Resource: "*"` — grants every action in
   every service except IAM. Equivalent to `PowerUserAccess` and includes
   destructive actions on all non-IAM services.

5. `kms:*` on `*` — KMS is a data-access multiplier. Any service that
   uses encryption (RDS, EBS, S3, Secrets Manager) becomes readable if the
   caller can decrypt with any key.

6. `ForAllValues:StringEquals: { "aws:RequestedRegion": "us-east-1" }` —
   looks like a region restriction, but `ForAllValues` evaluates true when
   the key is absent from the request. Use an explicit Deny on
   `aws:RequestedRegion` with `Null` check instead.

## Remediation tools

- **AWS IAM Access Analyzer** — generates least-privilege policies from
  CloudTrail activity. The fastest path from wildcard to scoped. Use the
  policy generation feature (not just findings).

- **`aws iam simulate-principal-policy`** — tests what actions a principal
  can actually perform. Pass the generated action list to validate a
  scoped policy before attaching it.

- **CloudTrail EventSource + EventName** — query CloudTrail to discover
  the exact API calls a workload makes, then build an allow-list. Use
  Athena for high-volume trails.

- **AWS managed policies vs inline** — prefer customer-managed or inline
  policies for least-privilege. AWS managed policies (AdministratorAccess,
  PowerUserAccess) reintroduce blast radius and update outside your
  control.

- **Permissions boundaries** — a JSON policy that caps the maximum
  effective permissions of a principal. Set on roles to prevent even an
  attached admin policy from granting full access. Often forgotten but
  critical for delegated administration.
