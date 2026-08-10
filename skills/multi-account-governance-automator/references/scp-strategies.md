# SCP Strategies for Multi-Account Governance — Reference

This reference catalogues the canonical SCP patterns used in multi-account
AWS organizations. Each entry includes the policy JSON, the attachment
target (root vs OU), the IAM-side implications, and known failure modes.

## Attachment targets and inheritance

SCP evaluation walks the OU chain: root -> parent OU -> child OU -> account.
Multiple SCPs at the same level are intersected. **Deny always wins** over
Allow. A policy at the root applies to ALL member accounts (NOT the
management account — SCPs do not govern the management account).

```
root (Guardrail SCP attached here)
├── Security OU (no additional SCP)
│   └── audit account        -> inherits root Guardrail SCP only
├── Workloads-Prod OU (Region throttle SCP attached)
│   └── prod-bu-a account    -> inherits root Guardrail + Prod Region throttle
├── Sandbox OU (Deny-list SCP attached)
│   └── sandbox-1 account    -> inherits root Guardrail + Sandbox Deny-list
└── Suspended OU (Deny-all SCP attached)
    └── quarantined account  -> inherits root Guardrail + Deny-all
```

## Pattern 1 — Guardrail (prevent specific dangerous actions)

Attach at the **root** so every member account inherits.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrganization",
      "Effect": "Deny",
      "Action": ["organizations:LeaveOrganization"],
      "Resource": "*"
    },
    {
      "Sid": "DenyRootActionsExceptMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableRootMFA",
        "iam:Get*",
        "iam:List*"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {"aws:PrincipalArn": ["arn:aws:iam::*:root"]}
      }
    },
    {
      "Sid": "DenyDisableGuardDuty",
      "Effect": "Deny",
      "Action": [
        "guardduty:DeleteDetector",
        "guardduty:UpdateDetector",
        "guardduty:DisassociateFromMasterAccount"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDeleteCloudTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:DeleteTrail",
        "cloudtrail:StopLogging",
        "cloudtrail:UpdateTrail"
      ],
      "Resource": "*"
    }
  ]
}
```

## Pattern 2 — Region throttle (limit regions)

Attach at the **workload OU** so only workload accounts are region-constrained.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "Action": ["*"],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "eu-west-1", "ap-southeast-1"]
        }
      }
    }
  ]
}
```

**Gotcha:** `aws:RequestedRegion` does NOT apply to global services (IAM,
Organizations, Route 53, CloudFront). A region-throttle SCP does not
constrain these. Use a separate Deny on global service actions where
applicable.

## Pattern 3 — Deny-list (forbid specific services)

Attach at the **sandbox OU** or at the root if org-wide.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnusedServices",
      "Effect": "Deny",
      "Action": [
        "alexaforbusiness:*",
        "qldb:*",
        "macie2:*",
        "cloud9:*",
        "kinesisvideo:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Pattern 4 — Allow-list (whitelist)

Powerful but operationally expensive. Use only for regulated OUs.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyEverythingExceptApproved",
      "Effect": "Deny",
      "NotAction": [
        "ec2:*", "s3:*", "iam:*", "lambda:*", "rds:*",
        "logs:*", "cloudwatch:*", "sns:*", "sqs:*",
        "sts:AssumeRole", "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Every new approved service requires a policy update. Use sparingly.

## Pattern 5 — Deny-all (for quarantined accounts)

Attach at the **Suspended OU**. No account should live here except
compromised accounts being investigated.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAll",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

**Warning:** do NOT attach this at the root. A Deny-all at root locks
every member account out. The management account is unaffected (SCPs do
not govern it) — but the org is effectively dead.

## Required IAM permissions

To create and attach SCPs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "organizations:CreatePolicy",
        "organizations:UpdatePolicy",
        "organizations:DeletePolicy",
        "organizations:AttachPolicy",
        "organizations:DetachPolicy",
        "organizations:ListPolicies",
        "organizations:ListPoliciesForTarget",
        "organizations:DescribePolicy",
        "organizations:EnablePolicyType",
        "organizations:DisablePolicyType"
      ],
      "Resource": "*"
    }
  ]
}
```

Must be in the management account. Member accounts cannot manage SCPs.

## SCP debugging

When a member account cannot perform an action that the operator expects
to be allowed:

1. List all SCPs attached at the root:
   `aws organizations list-policies-for-target --target-id <root-id> --filter SERVICE_CONTROL_POLICY`
2. List all SCPs attached at each OU in the chain to the account:
   `aws organizations list-policies-for-target --target-id <ou-id> --filter SERVICE_CONTROL_POLICY`
3. For each SCP, read the policy document:
   `aws organizations describe-policy --policy-id <id>`
4. Look for `Effect: Deny` statements that match the action. Remember:
   Deny always wins over Allow.

Use the **IAM Policy Simulator** with the SCP applied to verify the
effective permission set before attaching at scale.

## Common failure modes

- **`Allow *` at root does not override `Deny` at child.** Operators
  assume the allow-unblocks the deny. It does not. Remove the Deny or
  add a `StringNotEquals` condition that excludes the specific case.

- **SCP at root applies to ALL member accounts.** An operator attaches a
  region-throttle SCP at the root, intending to constrain only workload
  accounts — but now the audit account (which needs to run in a specific
  region) is also constrained. Attach at the workload OU, not root.

- **Management account is NOT governed by SCPs.** The console shows SCPs
  but the management account can perform any action regardless. Do not
  rely on SCPs to constrain management-account behavior.

- **Newly created accounts outside the OU tree do not inherit OU-level
  SCPs.** An account created at the root (not moved into an OU) inherits
  only root-level SCPs. Always move new accounts into the intended OU
  via `aws organizations move-account`.

## SCP enablement

SCPs must be enabled in the org root before they can be attached:

```bash
aws organizations enable-policy-type \
  --root-id <root-id> \
  --policy-type SERVICE_CONTROL_POLICY
```

Verify enablement:

```bash
aws organizations list-roots --query 'Roots[0].PolicyTypes[?Type==`SERVICE_CONTROL_POLICY`].Status'
# Must be "ENABLED"
```
