# SCP Library and Strategy Patterns Reference

Load this reference when authoring a new SCP. The templates below are
the canonical guardrail, throttle, and delegate patterns with full
JSON, condition keys, and known foot-guns documented.

## Strategy A — Guardrail (default)

**Definition:** keep the default `FullAWSAccess` attached to the root,
add explicit `Deny` statements for actions to block.

**Risk:** LOW. Additive; does not affect existing permissions.

### Library

#### Deny unapproved regions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnapprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "cloudfront:*",
        "iam:*",
        "route53:*",
        "support:*",
        "waf:*",
        "wafv2:*",
        "wellarchitected:*",
        "budgets:*",
        "ce:*",
        "cur:*",
        "aws-portal:*",
        "awsbillingconsole:*",
        "organizations:*",
        "health:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "eu-west-1", "us-west-2"]
        },
        "ArnNotLike": {
          "aws:CalledVia": ["cloudfront.amazonaws.com"]
        }
      }
    }
  ]
}
```

Global services (CloudFront, IAM, Route 53, billing, WAF global)
MUST be exempted via `NotAction` or they break region-less API calls.

#### Deny root user actions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRootUserAllActions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {"aws:PrincipalType": "root"}
      }
    }
  ]
}
```

#### Deny leave organization

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrg",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    }
  ]
}
```

#### Require SSE-KMS on S3 PutObject

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureS3Uploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

## Strategy B — Throttle

**Definition:** keep `FullAWSAccess`, add `Deny` with condition keys
that scope usage (region, instance type, quota).

**Risk:** MEDIUM. False positives block legitimate workflows.

#### Cap EC2 instance family

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnapprovedInstanceTypes",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:InstanceType": ["t3.micro", "t3.small", "t3.medium"]
        }
      }
    }
  ]
}
```

## Strategy C — Delegate / Allowlist (HIGH RISK)

**Definition:** remove `FullAWSAccess`, replace with explicit `Allow`
of approved services.

**Risk:** HIGH. Missing services = broken workflows. Test in staging
OU before promoting.

#### Allowlist approved services

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowApprovedServices",
      "Effect": "Allow",
      "Action": [
        "ec2:*", "s3:*", "rds:*", "lambda:*", "iam:*", "logs:*",
        "cloudwatch:*", "kms:*", "dynamodb:*", "sns:*", "sqs:*",
        "sts:*", "secretsmanager:*", "ssm:*", "efs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Use only after detaching `FullAWSAccess` from the root. Maintain a
registry of approved services; new AWS services require an allowlist
update.

## aws:CalledVia patterns

### Scope CloudFormation-driven IAM calls

```json
{
  "Sid": "AllowIAMViaCloudFormation",
  "Effect": "Allow",
  "Action": ["iam:CreateRole", "iam:PassRole", "iam:AttachRolePolicy"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:CalledVia": ["cloudformation.amazonaws.com"]
    }
  }
}
```

Without this pattern, an SCP that allows `iam:CreateRole` is
over-broad — any chained service can abuse it.

### Scope to first-and-last service

```json
{
  "Condition": {
    "StringEquals": {
      "aws:CalledViaFirst": "cloudformation.amazonaws.com",
      "aws:CalledViaLast": "servicecatalog.amazonaws.com"
    }
  }
}
```

Use when the chain order matters (e.g., service catalog invoking
CloudFormation).

## Deployment patterns

### Direct via AWS CLI

For ad-hoc or emergency SCP changes. Fast but un-audited beyond
CloudTrail.

```bash
aws organizations create-policy --content file://scp.json \
  --name my-scp --type SERVICE_CONTROL_POLICY
aws organizations attach-policy \
  --policy-id <POLICY_ID> --target-id <TARGET_ID>
```

### CloudFormation StackSets with Organizations

For managed, version-controlled SCP deployment. StackSets
auto-reconciles as accounts join the OU.

```yaml
# CloudFormation template
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MySCP:
    Type: AWS::Organizations::Policy
    Properties:
      Type: SERVICE_CONTROL_POLICY
      Name: deny-unapproved-regions
      Description: Deny usage outside approved regions
      Content: !Sub |
        {
          "Version": "2012-10-17",
          "Statement": [...]
        }
      Targets:
        - RootId: !Ref OrganizationRootId
```

Deploy via `aws cloudformation create-stack-set --permission-model
SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false`.

### Control Tower preventive controls

For Control Tower-managed landing zones, preventive controls ARE
SCPs. Customizing them requires the Control Tower `ControlTower`
service-linked role and the registered `aws-controltower-*` OUs.

## Known foot-guns

| Foot-gun | Symptom | Fix |
|---|---|---|
| Removed `FullAWSAccess` without allowlist | Every member account locked | Re-attach `FullAWSAccess` from management account |
| Region-deny without exempting global services | CloudFront / IAM / Route 53 broken | Add `NotAction` for global service prefixes |
| Deny at root, expected OU override | OU cannot re-allow | Move Deny to specific OU; use condition keys instead of blanket Deny |
| Used `Principal` element | Silently ignored | Replace with condition keys (`aws:PrincipalArn`, `aws:PrincipalType`) |
| Attached SCP to account expecting propagation | Only that account affected | Use OU-level attachment |
| Service-linked role broke | Trusted service fails | Test in staging OU first; some SLRs are exempt |
| Management account locked | Cannot recover | Use management account — SCPs do not apply to it |
