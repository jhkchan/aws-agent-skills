# Cross-Account Deployment and Deploy Action Contracts (CodePipeline V2)

Supplementary reference for the CodePipeline V2 Deployer skill. Use
when wiring cross-account CloudFormation / ECS / CodeDeploy deploys,
configuring KMS key policies for artifact sharing, or picking the
right deploy action for a target environment.

## Cross-account topology

```text
Source account (111111111111)                Target account (222222222222)
┌─────────────────────────────────┐          ┌────────────────────────────────┐
│ CodePipeline (V2)               │          │                                │
│  ↓ assume role                  │          │ CrossAccountCFNExecution role  │
│  ↓ sts:AssumeRole               │ ───────► │  trust: pipeline role in 1111  │
│ CloudFormation deploy action    │          │  perms: cloudformation:* on *  │
│  RoleArn: ...role/CFNExec       │          │                                │
└─────────────────────────────────┘          └────────────────────────────────┘
              │                                            │
              ▼                                            ▼
┌─────────────────────────────────┐          ┌────────────────────────────────┐
│ Artifact bucket                 │          │ Target stack                   │
│  KMS CMK key policy:            │          │  CloudFormation creates/updates│
│   - pipeline role: Decrypt,     │ ◄──────► │  resources in target account   │
│     GenerateDataKey             │          │                                │
│   - target CFN role: Decrypt    │          │                                │
└─────────────────────────────────┘          └────────────────────────────────┘
```

The three coordinated resources:

1. **KMS key in source account** — key policy grants:
   - Pipeline role in source account: `kms:Decrypt`,
     `kms:GenerateDataKey`, `kms:DescribeKey`.
   - Cross-account role in target account: `kms:Decrypt`,
     `kms:GenerateDataKey`.
2. **Cross-account IAM role in target account** — trust policy
   principal is the pipeline role ARN in the source account.
3. **Artifact bucket policy** — grants the target role `s3:GetObject`
   on the encrypted artifacts.

## KMS key policy template (source account)

```json
{
  "Version": "2012-10-17",
  "Id": "key-policy-pipeline-cross-account",
  "Statement": [
    {
      "Sid": "Enable IAM root permissions",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow pipeline role",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/my-pipeline-role"},
      "Action": ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
      "Resource": "*"
    },
    {
      "Sid": "Allow target account CFN role",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/CrossAccountCFNExecution"},
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*"
    }
  ]
}
```

## Target account IAM role trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:role/my-pipeline-role"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

The role's identity-based policy grants CloudFormation permissions on
the target stack (or `cloudformation:*` scoped by tag).

## Artifact bucket policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Allow pipeline role",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/my-pipeline-role"},
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-pipeline-artifacts",
        "arn:aws:s3:::my-pipeline-artifacts/*"
      ]
    },
    {
      "Sid": "Allow target account role",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/CrossAccountCFNExecution"},
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-pipeline-artifacts/*"
    }
  ]
}
```

## Common cross-account failure: KMS vs S3 misdiagnosis

Symptom: deploy action fails with `AccessDenied` on `s3:GetObject`.

Most operators assume the S3 bucket policy is wrong. In ~80% of cases
the S3 policy is correct and the **KMS key policy** is missing the
target role grant. Without `kms:Decrypt` on the KMS key, the target
role cannot decrypt the S3 object even though the S3 bucket policy
grants read.

**Diagnostic:**
```bash
aws kms get-key-policy --key-id <key-id> --policy-name default --output json | jq '.Statement[] | select(.Principal.AWS | contains("222222222222"))'
```

If the output is empty, the KMS policy does not grant the target
account. Add the grant, redeploy.

## Deploy action reference

### CloudFoundation CREATE_REPLACE (cross-account)

```yaml
ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
Configuration:
  ActionMode: CREATE_REPLACE     # create-or-update
  StackName: prod-my-service
  TemplatePath: BuildOutput::template.yaml
  Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM
  RoleArn: arn:aws:iam::222222222222:role/CrossAccountCFNExecution
  ParameterOverrides: '{"ImageUri":"#{BuildVars.IMAGE_URI}"}'
```

Action modes: `CHANGE_SET_REPLACE` (recommended for prod — explicit
change-set review), `CREATE_REPLACE` (create-or-update, simpler),
`DELETE_ONLY` (teardown), `EXECUTE_CHANGE_SET`.

### ECS deploy (direct image)

```yaml
ActionTypeId: {Category: Deploy, Owner: AWS, Provider: ECS, Version: 1}
Configuration:
  ClusterName: prod-cluster
  ServiceName: my-service
  Image1: #{BuildVars.IMAGE_URI}
```

The ECS deploy action creates a new task definition revision with the
provided image and updates the service. For multi-container tasks, use
`TaskDefinitionTemplatePath` with a JSON file mapping.

### CodeDeploy for EC2 (in-place or blue/green)

```yaml
ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CodeDeploy, Version: 1}
Configuration:
  ApplicationName: my-service-codedeploy
  DeploymentGroupName: prod-instances
```

For blue/green with target group swapping, the deployment group must
be configured with `deploymentStyle.option: WITH_TRAFFIC_CONTROL` and
a load balancer target group pair. EC2 instances must have the
CodeDeploy agent installed (via SSM or user-data).

### S3 deploy

```yaml
ActionTypeId: {Category: Deploy, Owner: AWS, Provider: S3, Version: 1}
Configuration:
  BucketName: prod-frontend-assets
  Extract: "true"               # unzip the artifact
  ObjectKey: ""                 # root of bucket (or sub-path)
```

Common for static site deploys. Pair with CloudFront invalidation
(via a downstream Lambda or CodeBuild action).

### Service Catalog

```yaml
ActionTypeId: {Category: Deploy, Owner: AWS, Provider: ServiceCatalog, Version: 1}
Configuration:
  ProductId: prod-abc123
  ProvisionedProductName: my-service-prod
```

Deploys a Service Catalog product (typically a CloudFormation stack
wrapped in a portfolio governance model).

## Manual approval action contract

```yaml
ActionTypeId: {Category: Approval, Owner: AWS, Provider: Manual, Version: 1}
Configuration:
  ExternalEntityLink: https://internal.example.com/change-record/CHG12345
  CustomData: "Approve to deploy to prod. Reviewer: oncall@example.com"
  NotificationArn: arn:aws:sns:us-east-1:111111111111:prod-approval
```

- The pipeline blocks until
  `aws codepipeline put-job-approval-result --job-id <id> --result status=Approved`
  is called (via the console button or CLI).
- `NotificationArn` (optional) sends an SNS notification when the
  approval is requested — wire to email/Slack subscriptions.
- Approval timeouts are NOT enforced. The pipeline waits indefinitely.
  Use an external scheduled Lambda to auto-reject approvals older
  than a threshold (e.g., 48 hours).

## CodeConnections (formerly CodeStar Connections)

GitHub / GitLab / Bitbucket sources require a CodeConnections
connection in `us-east-1`.

```bash
aws codeconnections create-connection --provider-type GitHub \
  --connection-name my-github-connection
# Returns a connection ARN in PENDING state

# Open the CodeCatalyst / Developer Tools console in us-east-1
# Click "Update pending connection" → authorize via GitHub OAuth
# State changes to AVAILABLE
```

The connection MUST be in `us-east-1` even if the pipeline is in
another region. Reference the full ARN in the source action:

```yaml
Configuration:
  ConnectionArn: arn:aws:codeconnections:us-east-1:111111111111:connection/abc-123
  FullRepositoryId: my-org/my-service
  BranchName: main
```

## AWS documentation

- **CodePipeline cross-account actions** — https://docs.aws.amazon.com/codepipeline/latest/userguide/cross-account.html
- **CloudFormation deploy action reference** — https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CloudFormation.html
- **ECS deploy action reference** — https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-ECS.html
- **CodeDeploy deploy action reference** — https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CodeDeploy.html
- **CodeConnections** — https://docs.aws.amazon.com/codeconnections/latest/userguide/welcome.html
- **KMS key policies for cross-account** — https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html

## Step 8 - Cross-account deployment (moved from SKILL.md)

Cross-account requires three coordinated resources:

1. **KMS key in source account** with a key policy granting the
   target account's deployment role `kms:Decrypt` and
   `kms:GenerateDataKey`.
2. **Cross-account IAM role in target account** that CloudFormation
   (or ECS / CodeDeploy) assumes. Trust policy allows the pipeline
   role from the source account.
3. **Artifact bucket policy** granting the target account's role
   `s3:GetObject` on the encrypted artifacts.

```bash
aws kms create-key --policy file://kms-key-policy.json
# Key policy grants: pipeline role (kms:GenerateDataKey, kms:Decrypt);
#                    target account deployment role (kms:Decrypt).

aws iam create-role --role-name CrossAccountCFNExecution \
  --assume-role-policy-document file://trust-policy.json
# Trust policy principal: arn:aws:iam::<source-account>:role/<pipeline-role>
```

**Anti-pattern:** sharing the artifact bucket without KMS. S3 bucket
policies alone do NOT grant cross-account access to encrypted objects
— the KMS key policy must also grant the target role. A bucket policy
without KMS policy produces "Access Denied" errors in the deploy
action that look like S3 issues but are actually KMS issues.

