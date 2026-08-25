# Constraint + Launch Role Templates — Service Catalog

Reference IAM policies, constraint JSON, and CloudFormation templates
for the LAUNCH / TAG_UPDATE / STACK_UPDATE / NOTIFICATION
constraints, plus the launch-role trust + permission policies.
Substitute `<REGION>`, `<ACCOUNT_ID>`, `<PORTFOLIO_ID>`,
`<PRODUCT_ID>`, `<ROLE_NAME>`, `<SNS_ARN>`, `<TAG_KEY>`,
`<TAG_VALUE>`, `<OU_ID>`, `<ORG_ID>` as needed.

## 1. Launch role — trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudformation.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

CloudFormation assumes this role during `CreateStack` for a Service
Catalog launch. The launching user passes this role via the LAUNCH
constraint; they do NOT need `iam:PassRole` themselves — Service
Catalog does the PassRole on their behalf.

## 2. Launch role — least-privilege permission policy (S3 example)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3BucketCreate",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketVersioning",
        "s3:PutBucketEncryption",
        "s3:PutBucketPolicy",
        "s3:PutBucketTagging",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": "arn:aws:s3:::sc-launched-*"
    },
    {
      "Sid": "S3ObjectNoOp",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::sc-launched-*"
    },
    {
      "Sid": "PassRoleTagCondition",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:ResourceTag/sc-launch-approved": "true"}
      }
    }
  ]
}
```

The `iam:PassRole` with a tag condition is the second line of
defense — even if the product template tries to pass an admin role,
the launch role will refuse unless that role is tagged
`sc-launch-approved=true`.

## 3. Launch role — least-privilege permission policy (VPC example)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VpcCreate",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc",
        "ec2:CreateSubnet",
        "ec2:CreateRouteTable",
        "ec2:CreateInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:CreateNatGateway",
        "ec2:AllocateAddress",
        "ec2:ModifyVpcAttribute",
        "ec2:AssociateRouteTable",
        "ec2:CreateRoute",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRoleTagCondition",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:ResourceTag/sc-launch-approved": "true"}
      }
    }
  ]
}
```

VPC resources do not all support tag-based IAM conditions, so the
`Resource: "*"` is necessary. The PassRole tag condition remains the
governance primitive.

## 4. LAUNCH constraint — STACK-based

```json
{
  "RoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>",
  "LocalRoleName": "<ROLE_NAME>"
}
```

`RoleArn` is the role CloudFormation assumes. `LocalRoleName` is used
when the product is launched in the same account; Service Catalog
maps the local role name to the appropriate ARN. For cross-account,
only `RoleArn` matters.

## 5. LAUNCH constraint — TEMPLATE-based (advanced)

```json
{
  "RoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>",
  "LocalRoleName": "<ROLE_NAME>",
  "Rules": [
    {
      "Name": "TeamScopedRole",
      "Rule": {
        "Match": {"LaunchRole": {"Tag": {"Team": "platform"}}},
        "Assign": "arn:aws:iam::<ACCOUNT_ID>:role/sc-launch-platform-vpc-role"
      }
    },
    {
      "Name": "Default",
      "Rule": {
        "Match": {"LaunchRole": {"Tag": {"Team": "*"}}},
        "Assign": "arn:aws:iam::<ACCOUNT_ID>:role/sc-launch-default-role"
      }
    }
  ]
}
```

Rules evaluate top-down; first match wins. The `Default` rule MUST
exist — without it, a non-matching user silently gets the bare
`RoleArn` (or worse, no constraint if `RoleArn` is empty).

## 6. TAG_UPDATE constraint

```json
{"TagUpdate": "NOT_ALLOWED"}
```

`NOT_ALLOWED` blocks all tag modifications to the launched stack
post-launch. `ALLOWED` (default) permits modifications. Use
`NOT_ALLOWED` for governance-heavy portfolios.

## 7. STACK_UPDATE constraint

```json
{"StackUpdate": "NOT_ALLOWED"}
```

`NOT_ALLOWED` blocks `UpdateStack` on the launched stack. The product
becomes immutable; only `TerminateProvisionedProduct` is permitted.
Use for compliance-bound products (e.g., audited configurations).

## 8. NOTIFICATION constraint

```json
{"NotificationArns": ["arn:aws:sns:<REGION>:<ACCOUNT_ID>:sc-launch-events"]}
```

Service Catalog publishes JSON events to the SNS topic on
`Launch`, `Update`, `Terminate`, and `Execute` events. The SNS topic
MUST exist before the constraint is applied; Service Catalog does not
validate the ARN at constraint-creation time.

## 9. LAUNCH_PERMISSION constraint (advanced)

```json
{"Principal": "arn:aws:iam::<ACCOUNT_ID>:role/<CONSUMER_ROLE>"}
```

Limits who can launch the product. Without this, any user with
`servicecatalog:LaunchProduct` on the portfolio can launch. Use
LAUNCH_PERMISSION to restrict a powerful product to a specific
consumer role even within the portfolio audience.

## 10. Constraint creation commands

```bash
# LAUNCH
aws servicecatalog create-constraint \
  --portfolio-id <PORTFOLIO_ID> \
  --product-id <PRODUCT_ID> \
  --parameters '{"RoleArn":"arn:aws:iam::<ACCOUNT_ID>:role/sc-launch-s3-role","LocalRoleName":"sc-launch-s3-role"}' \
  --type LAUNCH

# TAG_UPDATE
aws servicecatalog create-constraint \
  --portfolio-id <PORTFOLIO_ID> \
  --product-id <PRODUCT_ID> \
  --parameters '{"TagUpdate":"NOT_ALLOWED"}' \
  --type TAG_UPDATE

# NOTIFICATION
aws servicecatalog create-constraint \
  --portfolio-id <PORTFOLIO_ID> \
  --product-id <PRODUCT_ID> \
  --parameters '{"NotificationArns":["arn:aws:sns:<REGION>:<ACCOUNT_ID>:sc-launch-events"]}' \
  --type NOTIFICATION
```

Multiple constraints on the same product/portfolio pair are OR'd —
all are evaluated at launch time.

## 11. SNS topic for NOTIFICATION constraint

```bash
aws sns create-topic --name sc-launch-events
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:<REGION>:<ACCOUNT_ID>:sc-launch-events \
  --attribute-name Policy \
  --attribute-value '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"servicecatalog.amazonaws.com"},
      "Action":"sns:Publish",
      "Resource":"arn:aws:sns:<REGION>:<ACCOUNT_ID>:sc-launch-events",
      "Condition":{"ArnLike":{"aws:SourceArn":"arn:aws:servicecatalog:<REGION>:<ACCOUNT_ID>:*"}}
    }]
  }'
```

The topic policy MUST grant Service Catalog publish rights; otherwise
notifications silently fail.

### Step 5 — Configure constraints (creation CLI)

```bash
# Create the launch role first (Step 5 prereq)
aws iam create-role --role-name sc-launch-s3-role --assume-role-policy-document file://trust-policy.json
aws iam put-role-policy --role-name sc-launch-s3-role --policy-name s3-only --policy-document file://s3-only-policy.json

# Create the LAUNCH constraint
aws servicecatalog create-constraint \
  --portfolio-id $PORTFOLIO_ID \
  --product-id $PRODUCT_ID \
  --parameters '{"RoleArn":"arn:aws:iam::111111111111:role/sc-launch-s3-role","LocalRoleName":"sc-launch-s3-role"}' \
  --type LAUNCH
```
