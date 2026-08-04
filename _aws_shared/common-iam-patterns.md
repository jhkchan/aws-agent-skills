# Common IAM Patterns — Shared Reference

**Why this file exists:** Cross-cutting IAM reference loaded by any skill that
needs to evaluate IAM policy patterns — not just `iam-least-privilege-advisor`.
S3 bucket policies, EC2 launch profiles, and Lambda execution roles all
reference IAM concepts. This file is the lean shared extract; the deep
privilege-escalation taxonomy and remediation snippets live in
`iam-least-privilege-advisor/references/policy-analysis-guide.md`.

---

## The wildcard severity matrix

| Pattern | Severity | Why |
|---|---|---|
| `Action: "*", Resource: "*"` | CRITICAL | Full account compromise — any action on any resource |
| `Action: "iam:PassRole", Resource: "*"` | CRITICAL | Privilege escalation — can pass any role to an EC2/Lambda resource |
| `Action: "sts:AssumeRole", Resource: "*"` | CRITICAL | Can assume any role in the account (or cross-account if trust policy allows) |
| `Action: "s3:*", Resource: "*"` | HIGH | Full S3 access — read/write/delete any bucket |
| `Action: "ec2:*", Resource: "*"` | HIGH | Full EC2 access — modify instances, security groups, key pairs |
| `Action: "iam:*AccessKey*", Resource: "*"` | HIGH | Can create/delete/access keys for any user — credential theft |
| `Action: "lambda:*", Resource: "*"` | MEDIUM | Can modify Lambda functions (potential code injection) |
| `NotAction: "iam:*"` with `Resource: "*"` | HIGH | Allows everything EXCEPT IAM — still very broad |

## Privilege-escalation actions (the dangerous dozen)

These actions allow a principal to escalate beyond their intended scope:

1. `iam:PassRole` — pass a role to a service that then assumes it
2. `iam:CreateRole` + `iam:AttachRolePolicy` — create a new role with any policy
3. `iam:PutRolePolicy` — modify an existing role's inline policy
4. `sts:AssumeRole` — assume a different role (if trust policy allows)
5. `lambda:CreateFunction` + `iam:PassRole` — create a Lambda with a privileged role
6. `ec2:RunInstances` + `iam:PassRole` — launch an EC2 with a privileged instance profile
7. `cloudformation:CreateStack` + `iam:PassRole` — CloudFormation can assume any passed role
8. `glue:CreateDevEndpoint` + `iam:PassRole` — Glue dev endpoint with a privileged role
9. `iam:CreateAccessKey` — create new access keys for any user
10. `iam:UpdateLoginProfile` — reset any user's console password
11. `ssm:StartSession` — start a Session Manager session on any instance
12. `datapipeline:CreatePipeline` + `iam:PassRole` — Data Pipeline with a privileged role

## Condition-key bypass patterns

| Condition | Looks safe? | Actually safe? | Why |
|---|---|---|---|
| `aws:SourceIp: 10.0.0.0/8` | Yes | Medium | Restricts to RFC1918, but any resource in the VPC qualifies |
| `aws:SourceIp: 0.0.0.0/0` | No | No | This is the entire internet |
| `aws:Referer: example.com` | Yes | No | Trivially forgeable by any HTTP client |
| `aws:UserAgent: MyApp` | Yes | No | Trivially forgeable by any HTTP client |
| `aws:SourceVpce: vpce-xxx` | Yes | Yes | VPC Endpoint ID is not forgeable by the caller |
| `aws:SourceVpc: vpc-xxx` | Yes | Yes | VPC ID is network-level enforced |
| `aws:SourceAccount: 123456789012` | Yes | Yes | Account-level enforcement |
| `kms:ViaService: s3.us-east-1.amazonaws.com` | Yes | Yes | KMS-coupled service enforcement |

## Pre-flight safety checks before any IAM remediation

1. **Check if the policy is attached to a role used by a production service:**
   `aws iam list-entities-for-policy --policy-arn <arn>`
2. **Capture the current policy before modifying:**
   `aws iam get-role-policy --role-name <name> --policy-name <name> > backup.json`
3. **Prefer additive (create new scoped policy) over destructive (delete existing).**
4. **Test with an IAM policy simulator before applying:**
   `aws iam simulate-principal-policy --policy-source-arn <arn> --action-names s3:GetObject --resource-arns arn:aws:s3:::test-bucket/*`
