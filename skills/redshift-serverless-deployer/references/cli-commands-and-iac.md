# CLI Commands and IaC — Redshift Serverless Deployer

Full copy-pasteable CLI command sequence for all 11 deployment steps.
Variables to substitute: `<region>`, `<account-id>`, `<namespace>`,
`<workgroup>`, `<db-name>`, `<admin-user>`, `<admin-password>`,
`<subnet-group>`, `<subnet-ids>`, `<security-group-ids>`,
`<namespace-role>`, `<secret-id>`, `<kms-alias>`, `<base-rpu>`,
`<daily-rpu>`, `<monthly-rpu>`, `<dest-region>`, `<dest-kms-alias>`,
`<snapshot-interval>`, `<retention-days>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm KMS key exists and policy allows redshift-serverless
aws kms describe-key --key-id alias/redshift-prod \
  --query 'KeyMetadata.{Id:KeyId,State:KeyState,Mgr:KeyManager}'

# Confirm subnet group (if it already exists)
aws redshift-serverless describe-subnet-groups \
  --subnet-group-name <subnet-group> 2>/dev/null || echo "Subnet group does not exist yet"

# Confirm security group inbound rule for port 5439
aws ec2 describe-security-groups --group-ids sg-redshift-prod \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`5439`]'

# Confirm namespace IAM role trust policy
aws iam get-role --role-name <namespace-role> \
  --query 'Role.AssumeRolePolicyDocument'

# Confirm Secrets Manager secret exists (if used)
aws secretsmanager describe-secret --secret-id <secret-id> 2>/dev/null || echo "Secret does not exist yet"

# Confirm service quota (RPU-hours per region per account)
aws service-quotas get-service-quota \
  --service-code redshift-serverless \
  --quota-code L-XXXXXXXX \
  --query 'Quota.Value'
```

## Step 1: KMS key (customer-managed, recommended for production)

```bash
KEY_ID=$(aws kms create-key \
  --description "Redshift Serverless production key" \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "redshift-serverless.amazonaws.com"},
        "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:CreateGrant", "kms:DescribeKey"],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::<account-id>:root"},
        "Action": "kms:*",
        "Resource": "*"
      }
    ]
  }' \
  --query 'KeyMetadata.KeyId' --output text)

aws kms create-alias \
  --alias-name alias/redshift-prod \
  --target-key-id "$KEY_ID"

# Enable annual rotation (recommended)
aws kms enable-key-rotation --key-id "$KEY_ID"
echo "KMS key created: $KEY_ID (alias: alias/redshift-prod)"
```

## Step 2: Subnet group

```bash
aws redshift-serverless create-subnet-group \
  --subnet-group-name <subnet-group> \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --security-group-ids sg-redshift-prod \
  --tags Environment=production Application=analytics
```

Rules:
- At least 3 subnets across different AZs.
- Subnets in private IP ranges if public access is disabled (recommended).
- Security group inbound MUST allow port 5439 from analytics app SG.

## Step 3: IAM namespace role (for COPY/UNLOAD/S3/Glue)

```bash
aws iam create-role \
  --role-name <namespace-role> \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "redshift.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <namespace-role> \
  --policy-name redshift-data-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::ingest-bucket", "arn:aws:s3:::ingest-bucket/*"]
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": "arn:aws:s3:::unload-bucket/*"
      },
      {
        "Effect": "Allow",
        "Action": ["glue:GetTable", "glue:GetDatabase", "glue:GetPartitions"],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": ["kms:Decrypt", "kms:DescribeKey"],
        "Resource": "arn:aws:kms:<region>:<account-id>:key/*"
      }
    ]
  }'
```

## Step 4: Secrets Manager admin credential (recommended)

```bash
ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9!@#$%^&*' | head -c 32)

aws secretsmanager create-secret \
  --name <secret-id> \
  --secret-string "{
    \"username\": \"<admin-user>\",
    \"password\": \"$ADMIN_PASSWORD\",
    \"engine\": \"redshift\",
    \"port\": 5439
  }"

# Optional: enable managed rotation (requires managed rotation Lambda)
aws secretsmanager rotate-secret \
  --secret-id <secret-id> \
  --rotation-lambda-arn arn:aws:lambda:<region>:<account-id>:function:redshift-rotation \
  --rotation-rules AutomaticallyAfterDays=30
```

## Step 5: Namespace

```bash
aws redshift-serverless create-namespace \
  --namespace-name <namespace> \
  --admin-username <admin-user> \
  --admin-user-password "$ADMIN_PASSWORD" \
  --db-name <db-name> \
  --kms-key-id alias/redshift-prod \
  --default-iam-role-arn arn:aws:iam::<account-id>:role/<namespace-role> \
  --iam-roles arn:aws:iam::<account-id>:role/<namespace-role> \
  --security-group-ids sg-redshift-prod \
  --log-exports userlog connectionlog useractivitylog \
  --tags Environment=production Application=analytics
```

Wait for namespace to become AVAILABLE:

```bash
aws redshift-serverless get-namespace --namespace-name <namespace> \
  --query 'namespace.status' --output text
# Should return 'AVAILABLE'
```

## Step 6: Workgroup (compute)

```bash
aws redshift-serverless create-workgroup \
  --workgroup-name <workgroup> \
  --namespace-name <namespace> \
  --base-capacity <base-rpu> \
  --subnet-group-name <subnet-group> \
  --security-group-ids sg-redshift-prod \
  --publicly-accessible false \
  --config-parameters '[
    {"parameterKey":"enable_user_activity_logging","parameterValue":"true"},
    {"parameterKey":"enable_data_api","parameterValue":"true"},
    {"parameterKey":"enhanced_vpc_routing","parameterValue":"true"},
    {"parameterKey":"query_group","parameterValue":"analytics"},
    {"parameterKey":"max_query_execution_time","parameterValue":"14400"},
    {"parameterKey":"require_ssl","parameterValue":"true"}
  ]' \
  --tags Environment=production Application=analytics
```

Wait for workgroup to become AVAILABLE:

```bash
aws redshift-serverless get-workgroup --workgroup-name <workgroup> \
  --query 'workgroup.status' --output text
# Should return 'AVAILABLE'
```

## Step 7: Usage limits (cost controls)

```bash
# Daily limit
aws redshift-serverless put-usage-limit \
  --usage-type serverless-compute \
  --amount <daily-rpu> \
  --period daily \
  --breach-action log

# Monthly limit
aws redshift-serverless put-usage-limit \
  --usage-type serverless-compute \
  --amount <monthly-rpu> \
  --period monthly \
  --breach-action emit-metric
```

## Step 8: Data API verification

```bash
# Execute a test query via Data API
STATEMENT_ID=$(aws redshift-data execute-statement \
  --workgroup-name <workgroup> \
  --database <db-name> \
  --secret-arn arn:aws:secretsmanager:<region>:<account-id>:secret:<secret-id>-XXX \
  --sql "SELECT current_database(), current_user, current_time" \
  --query 'Id' --output text)

# Poll for completion
aws redshift-data describe-statement --id "$STATEMENT_ID" \
  --query 'Status' --output text
# Should return 'FINISHED'

# Fetch result
aws redshift-data get-statement-result --id "$STATEMENT_ID"
```

## Step 9: Query editor v2 IAM policy

```bash
aws iam create-policy \
  --policy-name RedshiftQueryEditorV2Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "redshift-serverless:DescribeWorkgroup",
          "redshift-serverless:DescribeNamespace",
          "redshift-serverless:ListWorkgroups",
          "redshift-serverless:ListNamespaces",
          "redshift-serverless:GetCredentials",
          "redshift-data:ExecuteStatement",
          "redshift-data:DescribeStatement",
          "redshift-data:GetStatementResult",
          "redshift-data:ListStatements",
          "redshift-data:CancelStatement",
          "secretsmanager:GetSecretValue"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:DescribeLogGroups", "logs:FilterLogEvents"],
        "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/redshift/*"
      }
    ]
  }'
```

Attach the policy to the IAM user/role that runs the query editor v2.

## Step 10: Snapshots and cross-Region copy

```bash
# Scheduled snapshot (source Region)
aws redshift-serverless create-scheduled-action \
  --scheduled-action-name analytics-snapshot-schedule \
  --namespace-name <namespace> \
  --schedule "rate(<snapshot-interval>)" \
  --target-action "{\"CreateSnapshot\":{\"NamespaceName\":\"<namespace>\",\"SnapshotName\":\"analytics-snapshot-$(date +%Y%m%d%H%M)\"}}" \
  --iam-role arn:aws:iam::<account-id>:role/<namespace-role> \
  --description "Automated production snapshot"

# Cross-Region snapshot copy: requires a destination-Region namespace
# with snapshot copy grant configured
DEST_KEY_ID=$(aws kms create-key \
  --description "Redshift Serverless DR key in <dest-region>" \
  --region <dest-region> \
  --query 'KeyMetadata.KeyId' --output text)

aws kms create-alias \
  --alias-name alias/redshift-dr \
  --target-key-id "$DEST_KEY_ID" \
  --region <dest-region>

# Snapshot copy grant
aws redshift create-snapshot-copy-grant \
  --snapshot-copy-grant-name analytics-copy-grant \
  --kms-key-id alias/redshift-dr \
  --region <dest-region>

# Configure cross-Region snapshot copy on the namespace
aws redshift-serverless update-namespace \
  --namespace-name <namespace> \
  --snapshot-copy-configurations '[{
    "DestinationRegion": "<dest-region>",
    "SnapshotCopyGrantName": "analytics-copy-grant",
    "RetentionPeriod": <retention-days>
  }]'
```

## Step 11: Post-deployment verification

```bash
aws redshift-serverless describe-workgroup --workgroup-name <workgroup>
aws redshift-serverless describe-namespace --namespace-name <namespace>
aws redshift-serverless list-usage-limits
aws redshift-serverless describe-scheduled-actions
aws secretsmanager describe-secret --secret-id <secret-id>
aws kms describe-key --key-id alias/redshift-prod
aws kms describe-key --key-id alias/redshift-dr --region <dest-region>
aws logs describe-log-groups --log-group-name-prefix /aws/redshift/<namespace>
aws redshift-serverless list-tags-for-resource --resource-arn arn:aws:redshift-serverless:<region>:<account-id>:namespace/<namespace>
```

## Terraform equivalents

### Namespace

```hcl
resource "aws_redshiftserverless_namespace" "analytics" {
  namespace_name      = "analytics-ns-prod"
  admin_username      = "admin"
  admin_user_password = data.aws_secretsmanager_secret_version.admin.secret_string
  db_name             = "dev"
  kms_key_id          = aws_kms_key.redshift.arn
  default_iam_role_arn = aws_iam_role.redshift_ns.arn
  iam_roles            = [aws_iam_role.redshift_ns.arn]
  log_exports          = ["userlog", "connectionlog", "useractivitylog"]

  tags = {
    Environment = "production"
    Application = "analytics"
  }
}
```

### Workgroup

```hcl
resource "aws_redshiftserverless_workgroup" "analytics" {
  workgroup_name = "analytics-wg-prod"
  namespace_name = aws_redshiftserverless_namespace.analytics.namespace_name
  base_capacity  = 128
  subnet_group_name = aws_redshiftserverless_subnet_group.analytics.id
  publicly_accessible = false

  config_parameter {
    parameter_key   = "enhanced_vpc_routing"
    parameter_value = "true"
  }
  config_parameter {
    parameter_key   = "enable_data_api"
    parameter_value = "true"
  }
  config_parameter {
    parameter_key   = "require_ssl"
    parameter_value = "true"
  }

  tags = {
    Environment = "production"
    Application = "analytics"
  }
}
```

### Usage limits

```hcl
resource "aws_redshiftserverless_usage_limit" "daily" {
  usage_type    = "serverless-compute"
  amount        = 500
  period        = "daily"
  breach_action = "log"
}

resource "aws_redshiftserverless_usage_limit" "monthly" {
  usage_type    = "serverless-compute"
  amount        = 12000
  period        = "monthly"
  breach_action = "emit-metric"
}
```

### Subnet group

```hcl
resource "aws_redshiftserverless_subnet_group" "analytics" {
  subnet_group_name = "redshift-subnet-group"
  subnet_ids        = [aws_subnet.a.id, aws_subnet.b.id, aws_subnet.c.id]
  security_group_ids = [aws_security_group.redshift.id]
}
```

## CloudFormation equivalents

### Namespace

```yaml
Type: AWS::RedshiftServerless::Namespace
Properties:
  NamespaceName: analytics-ns-prod
  AdminUsername: admin
  AdminUserPassword: !Sub "{{resolve:secretsmanager:redshift/admin:SecretString:password}}"
  DbName: dev
  KmsKeyId: !Ref RedshiftKMSKey
  DefaultIamRoleArn: !GetAtt RedshiftNSRole.Arn
  IamRoles:
    - !GetAtt RedshiftNSRole.Arn
  LogExports:
    - userlog
    - connectionlog
    - useractivitylog
  Tags:
    - Key: Environment
      Value: production
    - Key: Application
      Value: analytics
```

### Workgroup

```yaml
Type: AWS::RedshiftServerless::Workgroup
Properties:
  WorkgroupName: analytics-wg-prod
  NamespaceName: !Ref Namespace
  BaseCapacity: 128
  SubnetGroupName: !Ref SubnetGroup
  SecurityGroupIds:
    - !Ref RedshiftSecurityGroup
  PubliclyAccessible: false
  ConfigParameters:
    - ParameterKey: enhanced_vpc_routing
      ParameterValue: "true"
    - ParameterKey: enable_data_api
      ParameterValue: "true"
    - ParameterKey: require_ssl
      ParameterValue: "true"
  Tags:
    - Key: Environment
      Value: production
    - Key: Application
      Value: analytics
DependsOn: Namespace
```
