# Cross-Account IAM Role Chaining and Subscription Workflows — DataZone Domain Deployer

Deep reference on the cross-account IAM role chain for DataZone data
access (domain execution role → source account role, trust policies,
permission policies), subscription workflows (request-approve model,
approval routing, glossary-term-driven policies, auto-approval
configuration), and SSO federation for user management. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## The three-hop cross-account role chain

### Topology

```text
Hub account (111111111111) — DataZone domain
  ├── DataZone service assumes: AmazonDataZoneDomainExecution role
  │   (ARN: arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution)
  │
  └── Hub role assumes source account role via sts:AssumeRole

Source account (222222222222) — Data owner (S3 bucket, Redshift, RDS)
  └── DataZoneS3AccessRole (or DataZoneRedshiftAccessRole)
      → trust policy: allows hub execution role to assume
      → permission policy: allows reading data (s3:GetObject, etc.)

Consumer account (333333333333) — Data consumer (optional, for cross-account subscriptions)
  └── DataZoneConsumerRole
      → trust policy: allows DataZone to provision access in consumer account
      → permission policy: allows receiving data access grants
```

### Trust policy in the source account

The trust policy in the source account role must reference the FULL
ARN of the DataZone domain's execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "datazone-domain-aaa11122"
        }
      }
    }
  ]
}
```

**Why the full ARN, not the account ID:** using
`arn:aws:iam::111111111111:root` in the Principal allows ANY role
in the hub account to assume the source role — this is overly broad.
Using the specific execution role ARN restricts assumption to only
the DataZone service's role.

**External ID (optional but recommended):** the `sts:ExternalId`
condition adds an extra layer of security, ensuring only the specific
DataZone domain (identified by its external ID) can assume the role.

### Permission policy for S3 access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::my-customer-events",
        "arn:aws:s3:::my-customer-events/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartition"
      ],
      "Resource": "*"
    }
  ]
}
```

### Permission policy for Redshift access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift:DescribeClusters"
      ],
      "Resource": "arn:aws:redshift:us-east-1:222222222222:cluster:sales-dw-cluster"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:222222222222:secret:redshift-creds-*"
    }
  ]
}
```

### Verifying the role chain

```bash
# In the hub account — verify the domain execution role exists
aws iam get-role \
  --role-name AmazonDataZoneDomainExecution \
  --query 'Role.Arn' --output text

# In the source account — verify the source role trust policy
aws iam get-role \
  --role-name DataZoneS3AccessRole \
  --query 'Role.AssumeRolePolicyDocument' --output json

# Test the assumption from the hub account
aws sts assume-role \
  --role-arn arn:aws:iam::222222222222:role/DataZoneS3AccessRole \
  --role-session-name "datazone-test"
# If this returns credentials, the trust chain is working.
```

## Subscription workflows

### Request-approve model

```text
Subscription lifecycle states:
  PENDING → APPROVED → ACTIVE (access granted)
  PENDING → REJECTED (access denied)
  ACTIVE → REVOKED (access withdrawn)
```

1. **Consumer discovers asset** in the DataZone catalog.
2. **Consumer requests subscription** with a reason.
   - Status: `PENDING`
3. **Approver reviews request.**
   - Default approver: project owner.
   - Glossary-term-routed approver: data steward (for PII), executive
     (for Restricted).
4. **Approver approves or rejects.**
   - `APPROVED` → DataZone provisions IAM permissions / access grants.
   - `REJECTED` → no access.
5. **Consumer accesses data** through the provisioned mechanism:
   - S3: IAM permissions or S3 access point.
   - Redshift: schema/table-level grants.
   - RDS: connection provisioning.

### Glossary-term-driven approval routing

```text
Glossary term → Subscription policy mapping:

  "Public" (data classification term)
    → policy: AUTO_APPROVE
    → approver: none (auto-granted)

  "Internal" (data classification term)
    → policy: PROJECT_OWNER_APPROVAL
    → approver: project owner (default)

  "Confidential" (data classification term)
    → policy: DATA_STEWARD_APPROVAL
    → approver: data-steward@corp (designated steward)

  "Restricted" (data classification term)
    → policy: MULTI_LEVEL_APPROVAL
    → approvers: [data-steward@corp, compliance@corp, exec@corp]
    → all must approve
```

**How routing works:** when an asset is tagged with a glossary term,
the term's subscription policy is applied to any subscription request
for that asset. The request is routed to the designated approver(s)
instead of (or in addition to) the default project owner.

**Retroactivity:** glossary-term policies are NOT retroactive. If you
add a subscription policy to a glossary term after subscriptions are
already approved, existing subscriptions keep their current access.
Only NEW subscription requests are evaluated against the new policy.

### Configuring auto-approval for Public assets

```bash
# Set a glossary term subscription policy for auto-approval
aws datazone update-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --identifier "$(aws datazone list-glossary-terms \
    --domain-id "$DOMAIN_ID" \
    --query 'items[?name==`Public`].id' --output text)" \
  --subscription-policy '{
    "autoApproval": true,
    "comment": "Public assets auto-approved"
  }' \
  --region us-east-1
```

### Cross-account subscription provisioning

For cross-account subscriptions (consumer project in account
333333333333 subscribing to assets from a data source in account
222222222222), DataZone may deploy a CloudFormation stack in the
consumer account to provision the necessary IAM roles and access
grants.

```text
Cross-account subscription provisioning flow:
  1. Consumer (333333333333) requests subscription to asset
  2. Approver (data owner) approves
  3. DataZone deploys CloudFormation stack in consumer account (333333333333)
     → creates IAM role for consumer to access the data
     → creates S3 access point or Lake Formation grant
  4. Consumer can now read the data using the provisioned role
```

**Consumer account prerequisites:**
- IAM role allowing CloudFormation to create resources (AWSCloudFormationStackExecutionRole).
- RAM resource share acceptance (if the data owner shares via RAM).
- Lake Formation permissions (if the data is Lake Formation-governed).

## SSO federation

### IAM Identity Center integration

DataZone requires IAM Identity Center (formerly AWS SSO) for all
user management. IAM users are NOT supported.

```bash
# Verify IAM Identity Center is configured
aws sso-admin list-instances \
  --query 'Instances[0].{StoreId:IdentityStoreId,Arn:InstanceArn}' \
  --output table

# List SSO users
aws identitystore list-users \
  --identity-store-id "$(aws sso-admin list-instances \
    --query 'Instances[0].IdentityStoreId' --output text)" \
  --query 'Users[].{UserName:UserName,Email:Emails[0].Value,Name:DisplayName}' \
  --output table

# List SSO groups
aws identitystore list-groups \
  --identity-store-id "$(aws sso-admin list-instances \
    --query 'Instances[0].IdentityStoreId' --output text)" \
  --query 'Groups[].{GroupName:DisplayName,GroupId:GroupId}' \
  --output table
```

### Assigning users to DataZone projects

DataZone project membership is managed through SSO groups. Instead
of adding individual users, assign SSO groups as project members.

```text
SSO group → DataZone project role mapping:
  "data-engineers" (SSO group) → Project Member (analytics-domain / customer-analytics)
  "data-stewards" (SSO group) → Project Owner (analytics-domain / governance-project)
  "bi-analysts" (SSO group) → Project Viewer (analytics-domain / all projects)
```

### Domain admin assignment

The domain admin is the SSO user who created the domain. Additional
domain admins can be added via the DataZone console or API.

## Terraform cross-account example

```hcl
# Source account (222222222222) — IAM role for DataZone
resource "aws_iam_role" "datazone_s3_access" {
  provider = aws.source_account
  name     = "DataZoneS3AccessRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "datazone_s3_read" {
  provider = aws.source_account
  name     = "DataZoneS3ReadAccess"
  role     = aws_iam_role.datazone_s3_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.customer_events.arn,
          "${aws_s3_bucket.customer_events.arn}/*"
        ]
      }
    ]
  })
}

# Hub account (111111111111) — DataZone domain
resource "aws_datazone_domain" "analytics" {
  provider              = aws.hub_account
  name                  = "analytics-domain"
  domain_execution_role = aws_iam_role.datazone_execution.arn
  kms_key_identifier    = aws_kms_key.datazone.arn
}

resource "aws_datazone_project" "customer_analytics" {
  provider   = aws.hub_account
  domain_id  = aws_datazone_domain.analytics.id
  name       = "customer-analytics"
  description = "Customer analytics project"
}
```

## Common cross-account pitfalls

1. **Using account ID instead of full role ARN in trust policy.**
   The trust policy Principal should be the full ARN of the domain
   execution role, not the account root. This restricts assumption to
   the specific DataZone role.

2. **Forgetting the consumer account role.** Cross-account
   subscriptions need a role in the CONSUMER account too, not just
   the source account. DataZone deploys a CloudFormation stack in the
   consumer account to provision access.

3. **Not configuring glossary policies before publishing assets.**
   If glossary terms don't have subscription policies when assets are
   published, all subscriptions default to the project owner approval
   path. Adding policies later does NOT retroactively re-evaluate
   existing subscriptions.

4. **Assuming SSO is optional.** DataZone requires IAM Identity
   Center. Without SSO configured, the domain cannot be created.

5. **Missing Secrets Manager permissions for Redshift.** The
   Redshift connection requires a Secrets Manager secret for
   database credentials. The source account IAM role must have
   `secretsmanager:GetSecretValue` on the secret ARN.

## Expert heuristic: cross-account IAM role chaining (moved from SKILL.md)



A baseline model says "create a domain and add a data source." The
correct heuristic recognizes that cross-account data access requires a
three-hop IAM role chain.

```text
Role chaining for cross-account S3 data access:

  Hub account (DataZone domain):
    DataZone execution role: arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution
    → this role is assumed by the DataZone service

  Source account (S3 data):
    IAM role: arn:aws:iam::222222222222:role/DataZoneS3AccessRole
    → trust policy allows the hub account's execution role to assume it
    → permission policy allows s3:GetObject, s3:ListBucket on the data bucket

  Data flow:
    DataZone service
      → assumes hub execution role
      → hub execution role assumes source account role (sts:AssumeRole)
      → source account role reads S3 data
```

The trust policy in the source account is the critical piece:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Key implication:** without this trust policy, DataZone creates the
data source connection but every crawl and read operation fails with
Access Denied. This is the #1 cause of "my DataZone data source shows
no assets" tickets.



## Expert heuristic: subscription approval workflow (moved from SKILL.md)



The subscription workflow is the governance gate. It is a request-
approve model, NOT auto-grant.

```text
Subscription lifecycle:
  1. Consumer (project member) discovers an asset in the DataZone catalog
  2. Consumer requests a subscription to the asset
     → subscription status: PENDING
  3. Asset owner (project owner or delegated approver) reviews the request
     ├── Approve → subscription status: ACTIVE (access granted)
     └── Reject  → subscription status: REJECTED (access denied)
  4. If approved, DataZone provisions the access:
     ├── For S3: grants IAM permissions or S3 access point to the consumer
     ├── For Redshift: grants schema/table permissions
     └── For RDS: provisions the connection
  5. Consumer can now query/read the asset

Glossary-term-driven approval routing:
  ├── Asset tagged "Public" → auto-approve (or pre-approved policy)
  ├── Asset tagged "Internal" → project owner approval
  └── Asset tagged "PII" → data steward approval (multi-level)
```

**Key implication:** the subscription workflow must be designed before
publishing assets. Decide who approves what, and configure glossary
terms to route approval requests. Without a defined workflow,
subscriptions pile up in PENDING state indefinitely.



## Step 6 — subscription request and approval commands (moved from SKILL.md)



```bash
# Consumer requests a subscription to an asset
SUBSCRIPTION_ID=$(aws datazone create-subscription \
  --domain-id "$DOMAIN_ID" \
  --request-subscription '{
    "assetId": "<asset-id>",
    "projectId": "<consumer-project-id>",
    "requestReason": "Need access to customer events for Q3 analysis"
  }' \
  --region us-east-1 \
  --query 'id' --output text)

# Check subscription status (should be PENDING)
aws datazone get-subscription \
  --domain-id "$DOMAIN_ID" \
  --id "$SUBSCRIPTION_ID" \
  --query 'status' --region us-east-1

# Asset owner approves the subscription
aws datazone update-subscription \
  --domain-id "$DOMAIN_ID" \
  --id "$SUBSCRIPTION_ID" \
  --status APPROVED \
  --decision-comment "Approved for Q3 analysis" \
  --region us-east-1
```



## Step 7 — cross-account IAM role creation commands (moved from SKILL.md)



```bash
# In the SOURCE account (data owner, account 222222222222):
# Create an IAM role that the DataZone domain account can assume
aws iam create-role \
  --role-name DataZoneS3AccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach a permission policy to the role
aws iam put-role-policy \
  --role-name DataZoneS3AccessRole \
  --policy-name DataZoneS3ReadAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        "Resource": [
          "arn:aws:s3:::my-customer-events",
          "arn:aws:s3:::my-customer-events/*"
        ]
      }
    ]
  }'
```



## Step 10 — SSO verification commands (moved from SKILL.md)



```bash
# Verify SSO is configured
aws sso-admin list-instances \
  --query 'Instances[0].IdentityStoreId' --output text

# DataZone user management happens through the SSO directory.
# Users are assigned to DataZone projects as members or owners.
# The SSO directory is the source of truth for user identity.

# Verify SSO users
aws identitystore list-users \
  --identity-store-id "$(aws sso-admin list-instances \
    --query 'Instances[0].IdentityStoreId' --output text)" \
  --query 'Users[].{UserName:UserName,Email:Emails[0].Value}' \
  --output table
```


