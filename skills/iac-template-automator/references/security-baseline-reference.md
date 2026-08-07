# Security Baseline Reference — IaC Template Automator

This reference expands the 12 security baseline rules from SKILL.md into
the full cfn-nag / checkov rule mapping, with suppression patterns and
tool-specific examples.

## Rule precedence and gating

| Severity | Verdict effect | Rules |
|---|---|---|
| CRITICAL | Block all deploys (dev + prod) | 1, 2, 3 |
| HIGH | Block prod deploys; warn on dev | 4, 5, 6, 7, 8, 9 |
| MEDIUM | Warn; do not block | 10, 11, 12 |

A finding on any CRITICAL rule forces `VERDICT: MANUAL_STEP_REQUIRED`
regardless of other passing rules.

## Rule 1: No hardcoded secrets

**Detects:** Plaintext passwords, API keys, tokens in any template
property or default value.

| Tool | Rule ID | Detection |
|---|---|---|
| cfn-nag | W11 | IAM `Resources.*.Properties.PolicyDocument` with `Resource: "*"` (often paired) |
| cfn-nag | W73 | Lambda environment variables flagged as potentially sensitive |
| checkov | CKV_AWS_41 | Hardcoded secrets in Lambda environment |
| checkov | CKV_SECRET | Scan all string values against a regex secret pattern |

**CloudFormation correct pattern:**

```yaml
Parameters:
  # WRONG: Default: "MyPassword123!" — visible in CloudTrail
  DbPassword:
    Type: String
    NoEcho: true  # Masks in console, still in CloudTrail event payload
    Description: Provide via SSM or Secrets Manager reference

Resources:
  DBCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      # RIGHT: Secrets Manager resolution at deploy time
      MasterUsername: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:username}}"
      MasterUserPassword: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"

  DBSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      GenerateSecretString:
        SecretStringTemplate: '{"username":"appadmin"}'
        GenerateStringKey: password
        ExcludeCharacters: '"@/\\'
        PasswordLength: 32
```

**Terraform correct pattern:**

```hcl
resource "aws_db_instance" "main" {
  username = "appadmin"
  password = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string)["password"]
}

data "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
}
```

**Inline suppression (last resort — must include justification):**

```yaml
MyResource:
  Type: AWS::IAM::Role
  Metadata:
    cfn_nag:
      rules_to_suppress:
        - id: W11
          reason: "Logs role does not need Secrets Manager access — false positive."
```

## Rule 2: IAM least-privilege (no Action:* / Resource:*)

| Tool | Rule ID |
|---|---|
| cfn-nag | F3 (`*` action), F4 (`*` resource), F5 |
| checkov | CKV_AWS_1 (Admin policy), CKV_AWS_40 (Role wildcard) |
| tflint | `aws_iam_policy_document` with `actions = ["*"]` |

**Detection:**

```yaml
# TRIGGER F3 and F4:
Policies:
  - PolicyDocument:
      Statement:
        - Effect: Allow
          Action: '*'       # F3
          Resource: '*'     # F4
```

**Correct pattern (CDK construct grants):**

```typescript
// Prefer CDK's grant API — generates least-privilege automatically
bucket.grantRead(lambdaFn, 'data/*.json');
table.grantWriteData(lambdaFn);
```

**Correct pattern (Terraform data source):**

```hcl
data "aws_iam_policy_document" "app" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/data/*.json"]
  }
}
```

## Rule 3: IAM role principal scoping

| Tool | Rule ID |
|---|---|
| cfn-nag | F1 (`Principal: "*"`) |
| checkov | CKV_AWS_40 |

**Detection:**

```yaml
# F1
AssumeRolePolicyDocument:
  Statement:
    - Principal: { AWS: "*" }   # F1
      Action: sts:AssumeRole
```

**Correct pattern:**

```yaml
AssumeRolePolicyDocument:
  Statement:
    - Principal:
        AWS: !Sub "arn:aws:iam::${AWS::AccountId}:root"  # Account-scoped
      Action: sts:AssumeRole
      Condition:
        StringEquals:
          aws:SourceAccount: !Ref AWS::AccountId
        ArnLike:
          aws:SourceArn: !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:my-app-*"
```

## Rule 4: S3 PublicAccessBlockConfiguration

| Tool | Rule ID |
|---|---|
| cfn-nag | F14, F16, F18, F19, F20, F21, F22 |
| checkov | CKV_AWS_53, CKV_AWS_54, CKV_AWS_55, CKV_AWS_56, CKV_AWS_57, CKV_AWS_58 |

All four blocks MUST be `true`:

```yaml
PublicAccessBlockConfiguration:
  BlockPublicAcls: true
  IgnorePublicAcls: true
  BlockPublicPolicy: true
  RestrictPublicBuckets: true
```

## Rule 5: S3 BucketEncryption

| Tool | Rule ID |
|---|---|
| cfn-nag | W31 |
| checkov | CKV_AWS_18 (access logging), CKV_AWS_19 (encryption), CKV_AWS_20 (versioning) |

**SSE-KMS preferred over SSE-S3:**

```yaml
BucketEncryption:
  ServerSideEncryptionConfiguration:
    - ServerSideEncryptionByDefault:
        SSEAlgorithm: aws:kms
        KMSMasterKeyID: !Ref KmsKey
```

## Rule 6: Data store encryption at rest

| Service | cfn-nag | checkov |
|---|---|---|
| RDS | W92 | CKV_AWS_16, CKV_AWS_162 |
| DynamoDB | W49 (via `SSEDescription`) | CKV_AWS_28 |
| EBS | W83 | CKV_AWS_8 (default encryption) |
| Aurora | W92 | CKV_AWS_162 |
| ElastiCache | W41 | CKV_AWS_29 |
| Neptune | W92 | CKV_AWS_322 |

## Rule 7: RDS DeletionProtection (prod)

```yaml
DeletionPolicy: Retain
UpdateReplacePolicy: Retain
Properties:
  DeletionProtection: !If [IsProd, true, false]
```

`DeletionPolicy: Retain` is enforced for ALL environments — `DeletionProtection`
is the prod-specific gate.

## Rule 8: DynamoDB PointInTimeRecovery

| Tool | Rule ID |
|---|---|
| checkov | CKV_AWS_80 |
| cfn-nag | (no native rule — use checkov) |

```yaml
PointInTimeRecoverySpecification:
  PointInTimeRecoveryEnabled: true
```

## Rule 9: Lambda secrets via Secrets Manager

Lambda environment variables containing secrets MUST reference Secrets
Manager, never plaintext values.

| Tool | Rule ID |
|---|---|
| cfn-nag | W37 (environment variable may contain secret) |
| checkov | CKV_AWS_41 |

```yaml
# WRONG
Environment:
  Variables:
    API_KEY: sk-abc123def456  # W37

# RIGHT
Environment:
  Variables:
    SECRET_ARN: !Ref ApiSecret  # Reference only
Resources:
  ApiSecret:
    Type: AWS::SecretsManager::Secret
    Properties: { ... }
```

## Rule 10: Mandatory tags (Environment, Owner)

| Tool | Rule ID |
|---|---|
| checkov | CKV_AWS_8 (via provider default_tags) |

**Terraform (preferred — default_tags covers everything):**

```hcl
provider "aws" {
  default_tags {
    tags = {
      Environment = var.environment
      Owner       = "platform"
      ManagedBy   = "terraform"
    }
  }
}
```

**CloudFormation (per-resource — verbose):**

```yaml
Tags:
  - Key: Environment
    Value: !Ref Environment
  - Key: Owner
    Value: platform
```

**CDK (stack-level — preferred):**

```typescript
const app = new App();
new AppStack(app, 'prod-app', {
  tags: { Environment: 'prod', Owner: 'platform' },
});
```

## Rule 11: CloudFront TLS + HTTPS redirect

| Tool | Rule ID |
|---|---|
| checkov | CKV_AWS_174, CKV_AWS_341 |

```yaml
ViewerCertificate:
  MinimumProtocolVersion: TLSv1.2_2021
  SslSupportMethod: sni-only

DefaultCacheBehavior:
  ViewerProtocolPolicy: redirect-to-https
```

## Rule 12: No public admin/database ports

| Tool | Rule ID |
|---|---|
| cfn-nag | W2, W9, W40 |
| checkov | CKV_AWS_23, CKV_AWS_24, CKV_AWS_25, CKV_AWS_260, CKV_AWS_337 |

```yaml
# WRONG — W2, W9
SecurityGroupIngress:
  - CidrIp: 0.0.0.0/0
    FromPort: 22
    IpProtocol: tcp
    ToPort: 22
```

The skill never generates SG rules with `0.0.0.0/0` on ports 22, 3389,
1433, 3306, 5432, 6379, 27017, 9200.

## Cross-reference: detection coverage by tool

| Rule | cfn-lint | cfn-nag | checkov (CFN) | checkov (TF) | tflint |
|---|---|---|---|---|---|
| 1 No hardcoded secrets | - | W11, W73 | CKV_SECRET | CKV_SECRET | - |
| 2 IAM least-privilege | - | F3, F4, F5 | CKV_AWS_1 | CKV_AWS_1 | - |
| 3 IAM principal scope | - | F1 | CKV_AWS_40 | CKV_AWS_40 | - |
| 4 S3 BPA | - | F14, F16, F18-22 | CKV_AWS_53-58 | CKV_AWS_53-58 | - |
| 5 S3 encryption | - | W31 | CKV_AWS_19 | CKV_AWS_19 | - |
| 6 Data store encryption | - | W92, W49 | CKV_AWS_16, 28 | CKV_AWS_16, 28 | - |
| 7 RDS DeletionProtection | - | W33 | - | - | - |
| 8 DynamoDB PITR | - | - | CKV_AWS_80 | CKV_AWS_80 | - |
| 9 Lambda secrets | - | W37 | CKV_AWS_41 | CKV_AWS_41 | - |
| 10 Tags | - | - | CKV_AWS_8 | CKV_AWS_8 | - |
| 11 CloudFront TLS | - | - | CKV_AWS_174 | CKV_AWS_174 | - |
| 12 SG 0.0.0.0/0 admin | - | W2, W9, W40 | CKV_AWS_23-25 | CKV_AWS_23-25 | - |

**Run order in CI:** cfn-lint (spec) -> cfn-nag (security) -> checkov
(security, broader) -> tflint (TF-specific). All four are required; none
is a substitute for another.
