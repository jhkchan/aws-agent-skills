---
name: datazone-domain-deployer
description: 'Provisions Amazon DataZone data domains with production defaults: domain creation (create-datazone-domain), project management, data source connections (S3, Redshift, RDS), asset management (data inventory, glossary terms), metadata enrichment via Lambda-based auto-classification, subscription workflows (request-approve model), cross-account IAM role chaining for data access, blueprints (data lake, data warehouse), environment profiles, SSO federation for user management, and metadata forms. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a DataZone domain, setting up projects, configuring data source connections, establishing subscription workflows, configuring cross-account IAM roles, or deploying blueprints. Triggers: create datazone domain, datazone project, data source connection, subscription workflow, cross-account data access, datazone blueprint, environment profile, glossary governance, metadata enrichment, SSO federation datazone.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with datazone and ram access. Works with Terraform aws_datazone_domain / aws_datazone_project / aws_datazone_environment_blueprint resources and CloudFormation AWS::DataZone::Domain / AWS::DataZone::Project templates. Cross-account data access requires RAM resource share and IAM role trust policies.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, datazone, cloudops, deploy, analytics, provisioning, domain, project, subscription, glossary, blueprint, cross-account, iam-role-chaining, metadata
  dependencies: aws-orchestrator
  keywords: aws, datazone, data catalog, cloudops, deploy, provisioning, domain, project, data source, subscription, glossary, metadata, blueprint, environment profile, cross-account, iam role chaining, sso federation, asset management
  when_to_use: Invoke when the user wants to create an Amazon DataZone domain, manage projects, configure data source connections (S3, Redshift, RDS), set up subscription workflows (request-approve model), configure cross-account IAM role chaining for data access, deploy blueprints (data lake, data warehouse), configure environment profiles, establish glossary-driven governance, or enable metadata enrichment. Do NOT invoke for AWS Lake Formation (use Lake Formation skills), AWS Glue Data Catalog (use Glue skills), or Amazon Athena (use Athena skills).
---

# Amazon DataZone Domain Deployer

An AWS CloudOps agent skill that provisions Amazon DataZone data
domains with correct defaults. The skill walks the operator through
domain creation, project management, data source connections (S3,
Redshift, RDS), asset management with glossary terms, metadata
enrichment via Lambda-based auto-classification, subscription
workflows (request-approve model), cross-account IAM role chaining
for data access, blueprints (data lake, data warehouse), environment
profiles, SSO federation for user management, and metadata forms,
captures all governance and access decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create DataZone domain, DataZone project, data source connection,
subscription workflow, cross-account data access, DataZone blueprint,
environment profile, glossary governance, metadata enrichment, SSO
federation DataZone.

## STRICT output contract

When this skill is invoked with a DataZone-provisioning request
(create a domain, create a project, configure a data source, set up
subscriptions, configure cross-account IAM roles, deploy blueprints,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `DATAZONE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Domain creation | Core domain model |
| Step 2 — Project management | Project scoping |
| Step 3 — Data source connections (S3, Redshift, RDS) | Data ingestion |
| Step 4 — Asset management and glossary terms | Data inventory |
| Step 5 — Metadata enrichment (Lambda auto-classification) | Auto-tagging |
| Step 6 — Subscription workflows (request-approve) | Access governance |
| Step 7 — Cross-account IAM role chaining | Cross-account data access |
| Step 8 — Blueprints (data lake, data warehouse) | Environment templates |
| Step 9 — Environment profiles | Deployment targets |
| Step 10 — SSO federation and user management | Identity |
| Step 11 — Metadata forms | Custom metadata |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cross-account-and-subscriptions.md | IAM chaining + subscription detail |
| references/blueprints-and-governance.md | Blueprints + glossary detail |

## Mindset

**One-line takeaway:** Amazon DataZone is a data management service
that lets you catalog, govern, and share data across accounts and
teams. The domain is the top-level container; projects organize users
and data sources; subscriptions govern who can access what via a
request-approve model. Cross-account data access requires IAM role
chaining — the DataZone domain account assumes a role in the data
source account to read data. Glossary terms drive governance: assets
tagged with glossary terms inherit subscription policies.

Three misconceptions dominate DataZone misdesign at provisioning time:

- **"Creating the domain is enough to share data."** It is not. The
  domain is the container. To share data, you need: (1) a project with
  a data source connection, (2) the data source account must have an
  IAM role that DataZone can assume, (3) a subscription must be
  requested and approved. Creating the domain alone does nothing for
  data access. The cross-account IAM role chain is the #1 forgotten
  step.

- **"Subscriptions are automatically approved."** They are NOT by
  default. DataZone uses a request-approve model: a consumer requests
  access to an asset, and a project owner (or delegated approver)
  must approve the request. This is by design — it enforces data
  governance. Auto-approval can be configured but defeats the purpose
  of subscription governance.

- **"Glossary terms are just labels."** They are the governance
  mechanism. Glossary terms can carry subscription policies: an asset
  tagged "PII" might require the project owner's approval, while an
  asset tagged "Public" might allow auto-approval. The glossary is
  the policy engine, not just a labeling system. A baseline model
  treats glossary as cosmetic; it is structural.

## Configuration dependency graph (novel heuristic)

DataZone configurations are NOT independent. The domain must exist
before projects. Projects must exist before data sources. Data
sources require cross-account IAM roles. Subscriptions require assets
to be published. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Domain | AWS account with DataZone available; SSO configured | domain name must be unique; domain ARN is the root for all resources | project creation |
| Project | domain exists | project cannot be deleted if it has active subscriptions — must revoke first | data source, environment, user association |
| Data source (S3) | project exists; S3 bucket in source account; IAM role in source account allowing DataZone to assume | the IAM role in the source account is the #1 missing prerequisite; without it, DataZone cannot read data | asset auto-discovery |
| Data source (Redshift) | project exists; Redshift cluster/serverless namespace; IAM role; secrets manager secret | the Redshift connection requires a Secrets Manager secret for credentials | asset auto-discovery for Redshift |
| Asset | data source configured and crawled | assets are auto-discovered from the data source; they must be published (made visible) before subscriptions can reference them | subscription requests |
| Glossary term | domain exists | glossary terms are hierarchical (parent-child); attaching a term to an asset applies its subscription policy | policy-driven governance |
| Subscription | published asset exists; consumer project exists | subscription requires APPROVAL before access is granted — NOT automatic by default | data access for consumer |
| Cross-account IAM role | source account exists; IAM role with trust policy for DataZone domain account | the trust policy must reference the DataZone domain account ID and the domain's execution role; missing trust = access denied | cross-account data reads |
| Environment blueprint | domain exists; blueprint enabled | blueprints are AWS-managed templates (data lake, data warehouse); they define the environment's default configuration | environment creation |
| Environment profile | domain exists; blueprint enabled; project exists | profiles map blueprint defaults to specific account/region deployment targets | environment provisioning |
| Metadata enrichment (Lambda) | project exists; data source exists | Lambda function runs on asset creation/update; auto-classifies and tags assets with glossary terms | automated governance |

**The cross-account IAM role row is the one a baseline model misses.**
DataZone operates in a hub-and-spoke model: the domain account is the
hub; data source accounts are spokes. The domain account's execution
role must be allowed to assume a role in each source account. Without
this trust chain, DataZone creates the data source but cannot read
any data — all crawl and read operations fail silently with Access
Denied. The procedure below forces an explicit IAM role check.

**Cross-dependency gotchas:**
- The IAM role in the source account must trust the DataZone domain
  account's execution role ARN, not just the account ID. The full
  role ARN is required in the trust policy.
- Subscriptions are per-asset, not per-project. Each asset (table,
  file, view) needs its own subscription request.
- Glossary term subscription policies are applied at subscription
  time, not retroactively. If you add a policy to a glossary term
  after subscriptions are approved, existing subscriptions are NOT
  re-evaluated.
- Environment profiles determine WHERE environments are deployed
  (which account and region). The blueprint determines WHAT is
  deployed (data lake vs data warehouse defaults).
- SSO federation is required for domain user management. DataZone
  does NOT support IAM users. All users must come through IAM
  Identity Center (SSO).

## Expert heuristic: cross-account IAM role chaining

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

## Expert heuristic: subscription approval workflow

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

## Expert heuristic: glossary-driven governance

The glossary is not a tagging system — it is the policy engine.
Glossary terms define classification, ownership, and subscription
policies that are applied when assets are tagged.

```text
Glossary hierarchy example:
  Business Glossary (root)
  ├── Data Classification (category)
  │   ├── Public → auto-approve subscription policy
  │   ├── Internal → project owner approval
  │   ├── Confidential → data steward approval
  │   └── Restricted → executive approval (multi-level workflow)
  ├── Data Domain (category)
  │   ├── Customer Data → ownership: CRM team
  │   ├── Financial Data → ownership: Finance team
  │   └── Operational Data → ownership: Operations team
  └── Data Quality (category)
      ├── Certified → published, validated, ready for consumption
      └── Draft → not validated, subscriptions require additional review
```

When an asset is tagged with a glossary term, the term's subscription
policy is applied. An asset tagged "Public" gets auto-approval; an
asset tagged "Restricted" requires executive approval. This is the
governance mechanism that makes DataZone scalable — you don't approve
each subscription individually; you set policies at the glossary
level.

**Key implication:** design the glossary BEFORE publishing assets.
Adding glossary terms and policies after assets are published does
NOT retroactively apply to existing subscriptions. The glossary must
be the first governance artifact, not an afterthought.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports DataZone | DataZone is available in select regions | `aws datazone list-domains --region <region>` |
| IAM Identity Center (SSO) configured | DataZone requires SSO for user management — no IAM users | `aws sso-admin list-instances` |
| Domain name (3-63 chars, alphanumeric + hyphen) | Domain name must be unique | Naming convention check |
| Source account ID (if cross-account data) | Cross-account requires both account IDs | `aws sts get-caller-identity` in source account |
| IAM role in source account (if cross-account) | DataZone domain must assume a role in the source account to read data | `aws iam get-role --role-name DataZoneS3AccessRole` in source account |
| S3 bucket exists (if S3 data source) | Data source must reference an existing bucket | `aws s3api head-bucket --bucket <name>` |
| Redshift cluster/serverless namespace (if Redshift source) | Data source must reference an existing cluster | `aws redshift describe-clusters` or `aws redshift-serverless list-namespaces` |
| Secrets Manager secret for Redshift credentials | Redshift connection requires a secret with db credentials | `aws secretsmanager describe-secret --secret-id <id>` |
| KMS key for domain encryption (if CMK) | Domain data is encrypted; CMK provides auditability | `aws kms describe-key --key-id <key-id>` |
| IAM permissions for datazone:* | Provisioning requires domain/project create permissions | Verify IAM policy |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Domain creation

A DataZone domain is the top-level container for all data management
resources (projects, data sources, assets, glossaries).

```bash
# Create a DataZone domain
DOMAIN_ID=$(aws datazone create-domain \
  --name analytics-domain \
  --description "Centralized data governance domain for analytics" \
  --domain-execution-role arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution \
  --kms-key-id alias/datazone-cmk \
  --region us-east-1 \
  --query 'id' --output text)

echo "Domain ID: $DOMAIN_ID"
```

**Critical:** the `--domain-execution-role` must exist before creating
the domain. This role is assumed by the DataZone service to perform
cross-account operations (reading data sources, provisioning
environments). The role's trust policy must allow
`datazone.amazonaws.com` to assume it.

**Verify the domain is AVAILABLE:**

```bash
aws datazone get-domain \
  --domain-id "$DOMAIN_ID" \
  --query 'status' --region us-east-1
# Expected: AVAILABLE
```

## Step 2 — Project management

Projects organize users, data sources, and environments within a
domain. Each project has a project owner and members.

```bash
# Create a project in the domain
PROJECT_ID=$(aws datazone create-project \
  --domain-id "$DOMAIN_ID" \
  --name customer-analytics \
  --description "Customer analytics project with S3 and Redshift sources" \
  --region us-east-1 \
  --query 'id' --output text)

echo "Project ID: $PROJECT_ID"
```

**Project roles:**
- **Project owner:** can manage project settings, approve/reject
  subscriptions, add/remove members.
- **Project member:** can discover assets, request subscriptions,
  and consume published data.
- **Project viewer:** can browse the catalog but cannot request
  subscriptions.

## Step 3 — Data source connections (S3, Redshift, RDS)

Data source connections link external data stores to a DataZone
project. DataZone auto-discovers assets (tables, files, views) from
the connected source.

### S3 data source

```bash
# Create an S3 data source in the project
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name customer-events-s3 \
  --type S3 \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name customer-s3-connection \
    --type S3 \
    --s3 '{
      "location": {
        "bucketName": "my-customer-events",
        "key": "events/"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneS3AccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```

### Redshift data source

```bash
# Create a Redshift data source
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name sales-dw-redshift \
  --type REDSHIFT \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name sales-redshift-connection \
    --type REDSHIFT \
    --redshift '{
      "clusterId": "sales-dw-cluster",
      "databaseName": "sales_db",
      "credentials": {
        "secretArn": "arn:aws:secretsmanager:us-east-1:222222222222:secret:redshift-creds-xxx"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneRedshiftAccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```

### RDS data source

```bash
# Create an RDS data source
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name orders-rds \
  --type RDS \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name orders-rds-connection \
    --type RDS \
    --rds '{
      "instanceId": "orders-db",
      "databaseName": "orders",
      "credentials": {
        "secretArn": "arn:aws:secretsmanager:us-east-1:222222222222:secret:rds-creds-xxx"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneRDSAccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```

**Critical:** the `roleArn` in each connection references an IAM role
in the SOURCE account (222222222222). That role must have a trust
policy allowing the DataZone domain account's execution role to
assume it. Without this, DataZone cannot read any data from the
source.

## Step 4 — Asset management and glossary terms

Assets are auto-discovered from data sources. Each asset (S3 object,
Redshift table, RDS table) becomes a catalogable item. Assets must be
PUBLISHED before they appear in the catalog and can be subscribed to.

```bash
# List discovered assets (after a data source crawl)
aws datazone list-assets \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --region us-east-1

# Publish an asset (make it available in the catalog)
aws datazone update-asset \
  --domain-id "$DOMAIN_ID" \
  --identifier "$(aws datazone list-assets \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --query 'items[0].id' --output text)" \
  --status PUBLISHED \
  --region us-east-1
```

### Glossary terms

Glossary terms classify assets and drive subscription policies.

```bash
# Create a glossary term
aws datazone create-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --name "PII" \
  --long-description "Personally Identifiable Data — requires data steward approval for subscription" \
  --status ENABLED \
  --region us-east-1

# Attach a glossary term to an asset
aws datazone associate-glossary-term-with-asset \
  --domain-id "$DOMAIN_ID" \
  --glossary-term-id "$(aws datazone list-glossary-terms \
    --domain-id "$DOMAIN_ID" \
    --query 'items[?name==`PII`].id' --output text)" \
  --identifier "<asset-id>" \
  --region us-east-1
```

## Step 5 — Metadata enrichment (Lambda auto-classification)

Metadata enrichment uses Lambda functions to auto-classify assets when
they are discovered or updated. This automates glossary tagging.

```bash
# Create a metadata enrichment Lambda function
LAMBDA_ARN=$(aws lambda create-function \
  --function-name datazone-auto-classify \
  --runtime python3.12 \
  --role arn:aws:iam::111111111111:role/DataZoneEnrichmentRole \
  --handler index.lambda_handler \
  --zip-file fileb://enrichment.zip \
  --query 'FunctionArn' --output text)

# Register the enrichment function with the DataZone project
aws datazone create-environment \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name enrichment-environment \
  --blueprint-id default-data-lake \
  --region us-east-1 \
  --query 'id' --output text
```

The Lambda function receives asset metadata events from DataZone,
analyzes column names or data samples, and auto-tags the asset with
relevant glossary terms (e.g., tagging columns containing email
addresses with "PII").

```python
# Lambda handler for DataZone metadata enrichment
import json
import re

def lambda_handler(event, context):
    asset = event['detail']['asset']
    columns = asset.get('forms', {}).get('columnNameMapping', {})

    pii_patterns = {
        'email': r'^[a-z_]*email[a-z_]*$',
        'phone': r'^[a-z_]*phone[a-z_]*$',
        'ssn': r'^[a-z_]*ssn[a-z_]*$',
        'address': r'^[a-z_]*address[a-z_]*$',
    }

    detected_pii = False
    for col_name in columns:
        for pii_type, pattern in pii_patterns.items():
            if re.match(pattern, col_name, re.IGNORECASE):
                detected_pii = True
                break

    return {
        'assetId': asset['id'],
        'glossaryTerms': ['PII'] if detected_pii else ['Public'],
        'forms': {
            'autoClassification': {
                'detectedPII': detected_pii,
                'confidence': 0.85 if detected_pii else 1.0
            }
        }
    }
```

## Step 6 — Subscription workflows (request-approve model)

Subscriptions govern data access. A consumer requests access to a
published asset; the asset owner approves or rejects.

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

**Subscription statuses:** PENDING → APPROVED (access granted) |
REJECTED (access denied) | REVOKED (access withdrawn after approval).

**Glossary-term-driven routing:** assets tagged with glossary terms
that have subscription policies route approval requests to the
designated approver. For example, assets tagged "PII" route to the
data steward; assets tagged "Public" may auto-approve.

## Step 7 — Cross-account IAM role chaining

Cross-account data access requires a role chain: the DataZone domain
account's execution role assumes a role in the data source account.

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

**Critical:** the trust policy `Principal` must be the FULL ARN of
the DataZone domain's execution role, not just the account ID. Using
the account ID (`arn:aws:iam::111111111111:root`) is less secure
because it allows any role in the domain account to assume the source
role.

## Step 8 — Blueprints (data lake, data warehouse)

Blueprints are AWS-managed templates that define environment
defaults. DataZone provides two primary blueprints.

| Blueprint | Description | Default resources |
|---|---|---|
| **Default Data Lake** | S3-based data lake environment | S3 bucket, Glue database, Lake Formation permissions |
| **Default Data Warehouse** | Redshift-based data warehouse environment | Redshift cluster, database, IAM roles |

```bash
# List available blueprints
aws datazone list-environment-blueprints \
  --domain-id "$DOMAIN_ID" \
  --region us-east-1

# Enable a blueprint in the domain
aws datazone update-environment-blueprint \
  --domain-id "$DOMAIN_ID" \
  --blueprint-id default-data-lake \
  --enabled \
  --region us-east-1
```

**Blueprints define WHAT is provisioned** (data lake vs data
warehouse defaults). **Environment profiles determine WHERE it is
provisioned** (which account and region).

## Step 9 — Environment profiles

Environment profiles map blueprint defaults to specific deployment
targets (AWS account and region).

```bash
# Create an environment profile for the data lake blueprint
aws datazone create-environment-profile \
  --domain-id "$DOMAIN_ID" \
  --name production-data-lake \
  --description "Production data lake environment in the data account" \
  --blueprint-id default-data-lake \
  --environment-configuration '{
    "awsAccountId": "222222222222",
    "awsRegion": "us-east-1",
    "parameters": {
      "s3BucketName": "datazone-data-lake-prod",
      "glueDatabaseName": "datazone_catalog"
    }
  }' \
  --region us-east-1
```

**Environment profiles are project-scoped:** each project can have
its own profiles pointing to different accounts or regions.

## Step 10 — SSO federation and user management

DataZone uses IAM Identity Center (SSO) for user management. All
users must be provisioned through SSO — DataZone does NOT support IAM
users.

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

**User roles in DataZone:**
- **Domain admin:** can manage domain settings, all projects, and
  all blueprints.
- **Project owner:** can manage project settings, approve/reject
  subscriptions for assets in the project.
- **Project member:** can discover assets, request subscriptions,
  and consume published data.
- **Project viewer:** can browse the catalog but cannot request
  subscriptions.

**SSO groups** can be used to assign roles at scale. Instead of
adding individual users, add an SSO group as a project member.

## Step 11 — Metadata forms

Metadata forms are custom metadata templates that can be attached to
assets. They provide structured metadata beyond what the glossary
offers.

```bash
# Create a metadata form type
aws datazone create-form-type \
  --domain-id "$DOMAIN_ID" \
  --model '{
    "typeName": "DataQualityMetrics",
    "fields": {
      "freshnessHours": {"type": "number", "description": "Data freshness in hours"},
      "completenessPct": {"type": "number", "description": "Data completeness percentage"},
      "accuracyScore": {"type": "number", "description": "Data accuracy score 0-1"},
      "lastValidatedAt": {"type": "timestamp", "description": "Last validation timestamp"}
    }
  }' \
  --region us-east-1

# Attach metadata form to an asset
aws datazone post-form-data \
  --domain-id "$DOMAIN_ID" \
  --identifier "<asset-id>" \
  --form-name DataQualityMetrics \
  --content '{
    "freshnessHours": 2.5,
    "completenessPct": 98.7,
    "accuracyScore": 0.95,
    "lastValidatedAt": "2026-08-05T10:00:00Z"
  }' \
  --region us-east-1
```

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Auto-classification with SageMaker (2023-2024):** DataZone
  integrated SageMaker for ML-powered auto-classification of assets,
  detecting PII, data types, and column semantics without manual
  Lambda functions.

- **Cross-account subscription workflows (2024-2025):** Enhanced
  cross-account subscription support with automatic IAM role
  provisioning via CloudFormation stack deployment in the consumer
  account.

- **DataZone API GA (2024-2025):** The full DataZone API became
  generally available, enabling infrastructure-as-code (Terraform,
  CloudFormation) for domain, project, and data source management.

- **Glossary-driven policy engine (2024-2025):** Glossary terms can
  now carry complex subscription policies (multi-level approval,
  time-limited access, attribute-based access control).

- **Environment blueprint extensibility (2025-2026):** Custom
  blueprints beyond the default data lake and data warehouse, enabling
  domain-specific environment templates.

- **Metadata forms enhancement (2025-2026):** Structured metadata
  forms with validation rules, conditional fields, and automated
  enrichment via Lambda or SageMaker.

- **DataZone business-catalog (2025-2026):** Enhanced business
  catalog with searchable asset directory, data lineage, and impact
  analysis for governed data discovery at enterprise scale.

## NEVER do these things

1. **NEVER skip the cross-account IAM role setup.** DataZone operates
   in a hub-and-spoke model. The domain account's execution role must
   be able to assume a role in each source account. Without this
   trust chain, data sources connect but all reads fail silently with
   Access Denied.

2. **NEVER assume subscriptions are auto-approved.** DataZone uses a
   request-approve model by design. Subscriptions require explicit
   approval from the asset owner or delegated approver. Auto-approval
   can be configured but defeats the governance purpose.

3. **NEVER treat glossary terms as just labels.** Glossary terms are
   the policy engine. They carry subscription policies that determine
   approval routing. An asset tagged "PII" requires data steward
   approval; an asset tagged "Public" may auto-approve. Design the
   glossary BEFORE publishing assets.

4. **NEVER use the account ID in the cross-account trust policy
   instead of the full role ARN.** Using
   `arn:aws:iam::111111111111:root` in the Principal is less secure
   than using the full execution role ARN
   (`arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution`).
   The full ARN restricts assumption to the specific role.

5. **NEVER assume glossary policies are retroactive.** If you add a
   subscription policy to a glossary term after assets are published
   and subscriptions are approved, existing subscriptions are NOT re-
   evaluated. The glossary must be designed before publishing assets.

6. **NEVER try to use IAM users with DataZone.** DataZone requires
   IAM Identity Center (SSO) for all user management. IAM users are
   not supported. All users must be provisioned through the SSO
   directory.

7. **NEVER publish assets without glossary terms.** Assets without
   glossary terms have no governance policy. Every published asset
   should be classified with at least a data classification term
   (Public, Internal, Confidential, Restricted).

8. **NEVER forget to verify domain status is AVAILABLE before
   creating projects.** Domain creation is asynchronous. Creating a
   project before the domain is AVAILABLE will fail. Always poll the
   domain status.

9. **NEVER confuse blueprints with environment profiles.** Blueprints
   define WHAT is provisioned (data lake vs data warehouse defaults).
   Environment profiles define WHERE it is provisioned (which account
   and region). Both are needed.

10. **NEVER skip metadata enrichment for large catalogs.** Manual
    tagging of thousands of assets is unsustainable. Always configure
    Lambda-based or SageMaker-based auto-classification for metadata
    enrichment to keep glossary tags current.

## Output format

```text
DATAZONE: <domain-name> (<domain-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Domain: <domain-name> (<domain-id>) — AVAILABLE
  [✓|✗] Domain execution role: <role-arn>
  [✓|✗] SSO/IAM Identity Center: configured (identity store: <store-id>)
  [✓|✗] Project: <project-name> (<project-id>) — project owner: <owner>
  [✓|✗] Data source: <source-name> (S3 | Redshift | RDS) — connection established
  [✓|✗] Cross-account IAM role: <source-role-arn> — trust policy verified
  [✓|✗] Assets: discovered and published (<N> assets in catalog)
  [✓|✗] Glossary: <N> terms configured — subscription policies attached
  [✓|✗] Metadata enrichment: Lambda auto-classification configured
  [✓|✗] Subscription workflow: request-approve model — approver: <approver>
  [✓|✗] Blueprint: Default Data Lake | Default Data Warehouse — enabled
  [✓|✗] Environment profile: <profile-name> → account <acct>, region <region>
  [✓|✗] Encryption: KMS CMK (<kms-key-alias>) | AWS-managed key
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws datazone get-domain --domain-id <domain-id>
  aws datazone list-projects --domain-id <domain-id>
  aws datazone list-data-sources --domain-id <domain-id>
  aws datazone list-assets --domain-id <domain-id>
  aws datazone list-glossary-terms --domain-id <domain-id>
```

### Worked example — domain with S3 source and subscription governance

```text
DATAZONE: analytics-domain (domain-aaa11122)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain: analytics-domain (domain-aaa11122) — AVAILABLE
  [✓] Domain execution role: arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution
  [✓] SSO/IAM Identity Center: configured (identity store: d-abc12345)
  [✓] Project: customer-analytics (project-bbb22233) — project owner: data-steward@corp
  [✓] Data source: customer-events-s3 (S3) — connection established
  [✓] Cross-account IAM role: arn:aws:iam::222222222222:role/DataZoneS3AccessRole — trust policy verified
  [✓] Assets: discovered and published (42 assets in catalog)
  [✓] Glossary: 15 terms configured — subscription policies attached (PII → steward approval, Public → auto-approve)
  [✓] Metadata enrichment: Lambda auto-classification configured (datazone-auto-classify)
  [✓] Subscription workflow: request-approve model — approver: data-steward@corp
  [✓] Blueprint: Default Data Lake — enabled
  [✓] Environment profile: production-data-lake → account 222222222222, region us-east-1
  [✓] Encryption: KMS CMK (alias/datazone-cmk)
  [✓] Tags: Environment=production, Domain=analytics
VERIFICATION_COMMANDS:
  aws datazone get-domain --domain-id domain-aaa11122
  aws datazone list-projects --domain-id domain-aaa11122
  aws datazone list-data-sources --domain-id domain-aaa11122
  aws datazone list-assets --domain-id domain-aaa11122
  aws datazone list-glossary-terms --domain-id domain-aaa11122
```

## Error handling

### Data source crawl returns zero assets
- Cross-account IAM role trust policy is missing or incorrect. Verify
  the trust policy Principal is the full ARN of the DataZone domain's
  execution role. Verify the role has permissions on the S3 bucket /
  Redshift cluster / RDS instance.

### Domain creation fails with "InvalidDomainExecutionRole"
- The domain execution role does not exist or does not have the
  required permissions. Verify the role exists and has a trust policy
  allowing `datazone.amazonaws.com` to assume it.

### Subscriptions stuck in PENDING
- No approver has been configured for the project or the glossary
  term. Verify the project has an owner (who is the default approver).
  For glossary-term-routed approvals, verify the term has a designated
  approver.

### SSO users not visible in DataZone
- IAM Identity Center is not configured or the DataZone domain is not
  linked to the SSO directory. Verify SSO is enabled and the domain
  was created with SSO authentication enabled.

### Asset publishing fails
- The asset may be in DRAFT status or the project member may not have
  publish permissions. Verify the asset status and the user's project
  role (owner or member with publish permission).

### Cross-account subscription provisioning fails
- The consumer account does not have the required IAM role for
  receiving access. DataZone cross-account subscriptions may deploy a
  CloudFormation stack in the consumer account. Verify the consumer
  account has the necessary IAM permissions and service-linked roles.

## Domain

AWS CloudOps / Amazon DataZone Data Domain Provisioning, Data
Cataloging, Governance, and Cross-Account Data Sharing.

## AWS documentation

- **Amazon DataZone User Guide** — https://docs.aws.amazon.com/datazone/latest/userguide/what-is-datazone.html
- **Create domain** — https://docs.aws.amazon.com/datazone/latest/userguide/create-domain.html
- **Create project** — https://docs.aws.amazon.com/datazone/latest/userguide/create-project.html
- **Data source connections** — https://docs.aws.amazon.com/datazone/latest/userguide/data-sources.html
- **Subscription workflows** — https://docs.aws.amazon.com/datazone/latest/userguide/subscriptions.html
- **Cross-account access** — https://docs.aws.amazon.com/datazone/latest/userguide/cross-account-access.html
- **Glossary and governance** — https://docs.aws.amazon.com/datazone/latest/userguide/glossary.html
- **Blueprints** — https://docs.aws.amazon.com/datazone/latest/userguide/blueprints.html
- **Environment profiles** — https://docs.aws.amazon.com/datazone/latest/userguide/environment-profiles.html
- **Metadata enrichment** — https://docs.aws.amazon.com/datazone/latest/userguide/metadata-enrichment.html
- **IAM Identity Center integration** — https://docs.aws.amazon.com/datazone/latest/userguide/sso-integration.html
- **DataZone API** — https://docs.aws.amazon.com/datazone/latest/APIReference/Welcome.html
