# Blueprints and Glossary Governance — DataZone Domain Deployer

Deep reference on DataZone blueprints (data lake, data warehouse),
environment profiles (deployment target mapping), glossary-driven
governance (terms, subscription policies, classification hierarchy),
metadata enrichment (Lambda-based auto-classification, SageMaker
integration), and metadata forms (custom structured metadata).
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Blueprints

### What blueprints do

Blueprints are AWS-managed templates that define the default
configuration for DataZone environments. They specify WHAT resources
are provisioned when an environment is created in a project.

| Blueprint | Description | Default resources |
|---|---|---|
| **Default Data Lake** | S3-based data lake with Glue catalog | S3 bucket, Glue database, Lake Formation permissions, IAM roles |
| **Default Data Warehouse** | Redshift-based data warehouse | Redshift cluster or serverless namespace, database, IAM roles |

### Enabling a blueprint

```bash
# List available blueprints
aws datazone list-environment-blueprints \
  --domain-id "$DOMAIN_ID" \
  --query 'items[].{Name:name,Id:id,Provider:provider}' \
  --output table \
  --region us-east-1

# Enable the Default Data Lake blueprint
aws datazone update-environment-blueprint \
  --domain-id "$DOMAIN_ID" \
  --blueprint-id default-data-lake \
  --enabled \
  --region us-east-1

# Enable the Default Data Warehouse blueprint
aws datazone update-environment-blueprint \
  --domain-id "$DOMAIN_ID" \
  --blueprint-id default-data-warehouse \
  --enabled \
  --region us-east-1
```

### Blueprint vs environment profile

```text
Blueprint = WHAT is provisioned (data lake vs data warehouse defaults)
Environment profile = WHERE it is provisioned (which account and region)

Example:
  Blueprint: Default Data Lake
  → defines: S3 bucket, Glue database, Lake Formation setup

  Environment profile: production-data-lake
  → maps to: account 222222222222, region us-east-1
  → overrides: bucket name = datazone-data-lake-prod, Glue DB = datazone_catalog

  Environment profile: staging-data-lake
  → maps to: account 444444444444, region us-east-1
  → overrides: bucket name = datazone-data-lake-staging, Glue DB = datazone_catalog_stg
```

Both blueprint AND environment profile are needed. The blueprint
provides the template; the profile provides the deployment target.

### Custom blueprints (2025-2026 feature)

Custom blueprints extend beyond the default data lake and data
warehouse templates. They enable domain-specific environment
templates:

```bash
# Create a custom blueprint (extensibility feature)
aws datazone create-environment-blueprint \
  --domain-id "$DOMAIN_ID" \
  --name custom-analytics-environment \
  --description "Custom analytics environment with SageMaker Studio and Athena workgroup" \
  --blueprint-spec '{
    "resources": [
      {"type": "S3Bucket", "properties": {"bucketName": "analytics-workspace"}},
      {"type": "SageMakerStudioDomain", "properties": {"domainName": "analytics-studio"}},
      {"type": "AthenaWorkGroup", "properties": {"workGroupName": "analytics-athena"}}
    ]
  }' \
  --region us-east-1
```

## Environment profiles

### Creating an environment profile

```bash
# Create an environment profile mapped to a specific account and region
aws datazone create-environment-profile \
  --domain-id "$DOMAIN_ID" \
  --name production-data-lake \
  --description "Production data lake environment" \
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

### Multiple profiles per blueprint

A single blueprint can have multiple profiles, each targeting a
different account or region:

```text
Blueprint: Default Data Lake
  ├── Profile: production-data-lake → account 222222222222, us-east-1
  ├── Profile: staging-data-lake → account 444444444444, us-east-1
  └── Profile: dr-data-lake → account 555555555555, us-west-2
```

Each project selects the appropriate profile when creating an
environment.

## Glossary-driven governance

### Glossary structure

The glossary is a hierarchical taxonomy of terms that classify data
assets. Terms are organized into categories and can have parent-child
relationships.

```text
Business Glossary (root)
│
├── Data Classification (category)
│   ├── Public
│   │   └── subscription policy: AUTO_APPROVE
│   ├── Internal
│   │   └── subscription policy: PROJECT_OWNER_APPROVAL
│   ├── Confidential
│   │   └── subscription policy: DATA_STEWARD_APPROVAL
│   └── Restricted
│       └── subscription policy: MULTI_LEVEL_APPROVAL
│
├── Data Domain (category)
│   ├── Customer Data → ownership: CRM team (crm-team@corp)
│   ├── Financial Data → ownership: Finance team (finance@corp)
│   ├── Operational Data → ownership: Operations (ops@corp)
│   └── HR Data → ownership: HR team (hr@corp)
│
├── Data Quality (category)
│   ├── Certified → validated, published, ready for consumption
│   └── Draft → not validated, subscriptions require additional review
│
└── Retention (category)
    ├── 1-Year Retention
    ├── 3-Year Retention
    ├── 7-Year Retention
    └── Indefinite
```

### Creating glossary terms

```bash
# Create a category
aws datazone create-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --name "Data Classification" \
  --long-description "Classification levels for data assets" \
  --status ENABLED \
  --region us-east-1

# Create a term under the category
aws datazone create-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --name "PII" \
  --long-description "Personally Identifiable Data — requires data steward approval" \
  --status ENABLED \
  --parent-term-id "$(aws datazone list-glossary-terms \
    --domain-id "$DOMAIN_ID" \
    --query 'items[?name==`Data Classification`].id' --output text)" \
  --region us-east-1
```

### Attaching subscription policies to glossary terms

```bash
# Auto-approve policy for Public assets
aws datazone update-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --identifier "<public-term-id>" \
  --subscription-policy '{
    "autoApproval": true,
    "comment": "Public assets are auto-approved"
  }' \
  --region us-east-1

# Data steward approval for PII assets
aws datazone update-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --identifier "<pii-term-id>" \
  --subscription-policy '{
    "autoApproval": false,
    "approver": {
      "userIdentifier": "data-steward@corp"
    },
    "comment": "PII assets require data steward approval"
  }' \
  --region us-east-1

# Multi-level approval for Restricted assets
aws datazone update-glossary-term \
  --domain-id "$DOMAIN_ID" \
  --identifier "<restricted-term-id>" \
  --subscription-policy '{
    "autoApproval": false,
    "approvers": [
      {"userIdentifier": "data-steward@corp"},
      {"userIdentifier": "compliance@corp"},
      {"userIdentifier": "exec@corp"}
    ],
    "approvalType": "ALL_MUST_APPROVE",
    "comment": "Restricted assets require multi-level approval"
  }' \
  --region us-east-1
```

### Tagging assets with glossary terms

```bash
# Tag an asset with a glossary term
aws datazone associate-glossary-term-with-asset \
  --domain-id "$DOMAIN_ID" \
  --glossary-term-id "<pii-term-id>" \
  --identifier "<asset-id>" \
  --region us-east-1
```

When an asset is tagged, the term's subscription policy is applied to
all future subscription requests for that asset.

## Metadata enrichment

### Lambda-based auto-classification

Metadata enrichment uses Lambda functions that are triggered when
assets are discovered or updated. The function analyzes the asset
metadata and auto-tags it with glossary terms.

```python
# Lambda function: datazone-auto-classify
# Triggered by DataZone asset creation/update events

import json
import re

# PII detection patterns based on column name
PII_PATTERNS = {
    'email': r'^[a-z_]*email[a-z_]*$',
    'phone': r'^[a-z_]*(phone|mobile|tel)[a-z_]*$',
    'ssn': r'^[a-z_]*(ssn|social_security)[a-z_]*$',
    'address': r'^[a-z_]*(address|street|city|zip|postal)[a-z_]*$',
    'name': r'^[a-z_]*(first_name|last_name|full_name|customer_name)[a-z_]*$',
    'dob': r'^[a-z_]*(dob|birth_date|date_of_birth)[a-z_]*$',
    'credit_card': r'^[a-z_]*(credit_card|cc_number|card_number)[a-z_]*$',
}

def lambda_handler(event, context):
    """
    Event structure from DataZone:
    {
        'detail': {
            'asset': {
                'id': 'asset-xxx',
                'name': 'customer_events',
                'type': 'S3_OBJECT',
                'forms': {
                    'columnNameMapping': {
                        'col1': 'customer_email',
                        'col2': 'event_timestamp',
                        'col3': 'phone_number',
                        'col4': 'event_type'
                    }
                }
            }
        }
    }
    """
    asset = event['detail']['asset']
    columns = asset.get('forms', {}).get('columnNameMapping', {})

    detected_pii_types = []
    for col_name in columns.values():
        for pii_type, pattern in PII_PATTERNS.items():
            if re.match(pattern, col_name, re.IGNORECASE):
                detected_pii_types.append(pii_type)

    # Determine glossary term based on PII detection
    if detected_pii_types:
        glossary_terms = ['PII']
        classification = 'Confidential'
    else:
        glossary_terms = ['Public']
        classification = 'Public'

    # Return enrichment result
    return {
        'assetId': asset['id'],
        'glossaryTerms': glossary_terms,
        'forms': {
            'autoClassification': {
                'classification': classification,
                'detectedPIITypes': detected_pii_types,
                'confidence': 0.95 if detected_pii_types else 1.0,
                'classifiedAt': event.get('time', ''),
                'classifiedBy': 'datazone-auto-classify-lambda'
            }
        }
    }
```

### Registering the enrichment function

```bash
# Create the Lambda function
LAMBDA_ARN=$(aws lambda create-function \
  --function-name datazone-auto-classify \
  --runtime python3.12 \
  --role arn:aws:iam::111111111111:role/DataZoneEnrichmentRole \
  --handler index.lambda_handler \
  --zip-file fileb://enrichment.zip \
  --environment '{"Variables": {"DATAZONE_DOMAIN_ID": "'"$DOMAIN_ID"'"}}' \
  --query 'FunctionArn' --output text)

# Add DataZone as a trigger source
aws lambda add-permission \
  --function-name datazone-auto-classify \
  --statement-id datazone-invoke \
  --action lambda:InvokeFunction \
  --principal datazone.amazonaws.com \
  --source-arn "arn:aws:datazone:us-east-1:111111111111:domain/$DOMAIN_ID"
```

### SageMaker-based auto-classification (2023-2024 feature)

For more sophisticated classification (e.g., analyzing data samples
for PII content, not just column names), DataZone integrates with
SageMaker:

```bash
# Create a SageMaker-based enrichment
aws datazone create-metadata-enrichment \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name sagemaker-pii-detection \
  --type SAGEMAKER \
  --configuration '{
    "endpointName": "pii-detection-endpoint",
    "inputMapping": {
      "assetId": "$.asset.id",
      "sampleData": "$.asset.forms.sampleData"
    },
    "outputMapping": {
      "glossaryTerms": "$.predictedTerms",
      "confidence": "$.confidenceScore"
    }
  }' \
  --region us-east-1
```

## Metadata forms

### What metadata forms do

Metadata forms are custom metadata templates that provide structured
metadata beyond what the glossary offers. They can include data
quality metrics, SLA information, ownership details, or any custom
field structure.

### Creating a metadata form type

```bash
# Define a Data Quality Metrics form type
aws datazone create-form-type \
  --domain-id "$DOMAIN_ID" \
  --model '{
    "typeName": "DataQualityMetrics",
    "description": "Data quality metrics for assets",
    "fields": {
      "freshnessHours": {
        "type": "number",
        "description": "Data freshness in hours",
        "required": true
      },
      "completenessPct": {
        "type": "number",
        "description": "Data completeness percentage (0-100)",
        "required": true,
        "validation": {"min": 0, "max": 100}
      },
      "accuracyScore": {
        "type": "number",
        "description": "Data accuracy score (0.0-1.0)",
        "validation": {"min": 0.0, "max": 1.0}
      },
      "lastValidatedAt": {
        "type": "timestamp",
        "description": "Last validation timestamp"
      },
      "validatedBy": {
        "type": "string",
        "description": "Validation method (manual, automated, enrichment)"
      }
    }
  }' \
  --region us-east-1
```

### Attaching metadata form data to an asset

```bash
# Attach form data to an asset
aws datazone post-form-data \
  --domain-id "$DOMAIN_ID" \
  --identifier "<asset-id>" \
  --form-name DataQualityMetrics \
  --content '{
    "freshnessHours": 2.5,
    "completenessPct": 98.7,
    "accuracyScore": 0.95,
    "lastValidatedAt": "2026-08-05T10:00:00Z",
    "validatedBy": "automated"
  }' \
  --region us-east-1
```

### Conditional and auto-filled forms

Metadata forms can be configured to auto-fill from enrichment
functions. For example, the `DataQualityMetrics` form can be
populated by a Lambda that runs data quality checks on the asset.

```text
Form auto-fill flow:
  1. Asset is discovered/updated in DataZone
  2. Lambda enrichment function is triggered
  3. Lambda runs data quality checks (row count, null %, freshness)
  4. Lambda fills the DataQualityMetrics form with results
  5. Form data is visible in the DataZone catalog
```

## Terraform governance example

```hcl
# Glossary terms with subscription policies
resource "aws_datazone_glossary_term" "pii" {
  domain_id = aws_datazone_domain.analytics.id
  name      = "PII"
  long_description = "Personally Identifiable Data"
  status    = "ENABLED"

  subscription_policy = jsonencode({
    autoApproval = false
    approver = {
      userIdentifier = "data-steward@corp"
    }
  })
}

resource "aws_datazone_glossary_term" "public" {
  domain_id = aws_datazone_domain.analytics.id
  name      = "Public"
  long_description = "Public data, no restrictions"
  status    = "ENABLED"

  subscription_policy = jsonencode({
    autoApproval = true
  })
}

# Environment blueprint enablement
resource "aws_datazone_environment_blueprint" "data_lake" {
  domain_id    = aws_datazone_domain.analytics.id
  blueprint_id = "default-data-lake"
  enabled      = true
}

# Environment profile
resource "aws_datazone_environment_profile" "production" {
  domain_id    = aws_datazone_domain.analytics.id
  name         = "production-data-lake"
  blueprint_id = aws_datazone_environment_blueprint.data_lake.blueprint_id

  environment_configuration = jsonencode({
    awsAccountId = "222222222222"
    awsRegion    = "us-east-1"
    parameters = {
      s3BucketName    = "datazone-data-lake-prod"
      glueDatabaseName = "datazone_catalog"
    }
  })
}
```

## Expert heuristic: glossary-driven governance (moved from SKILL.md)



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



## Step 4 — asset listing and publishing commands (moved from SKILL.md)



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



## Step 4 — glossary term creation and association commands (moved from SKILL.md)



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



## Step 5 — metadata enrichment Lambda walkthrough (moved from SKILL.md)



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



## Step 8 — blueprint listing and enablement commands (moved from SKILL.md)



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



## Step 9 — environment profile creation command (moved from SKILL.md)



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



## Step 11 — metadata form commands (moved from SKILL.md)



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


