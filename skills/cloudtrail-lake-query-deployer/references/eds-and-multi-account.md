# Event Data Stores and Multi-Account — CloudTrail Lake Query Deployer

Deep reference on EDS creation, event type immutability, advanced
event selectors for data events, multi-account Organization EDS,
retention management, data protection policies, and Athena
federation. Loaded on demand by the skill.

## Event data store types and immutability

### EDS types

| Type | Ingests | Selectors | Immutable? |
|---|---|---|---|
| Management | Control plane API calls | None (all management events) | Type is immutable |
| Data | Data plane API calls (S3, Lambda, DynamoDB) | Advanced event selectors required | Type is immutable |
| Insights | Anomalous API patterns | Insight selectors | Type is immutable |
| Network | VPC flow-style network events | Network event selectors | Type is immutable |

**Critical:** the event type is set at EDS creation and CANNOT be
changed. If you need both management and data events, create TWO EDS
(one for each type). A single EDS cannot ingest both management and
data events.

### Creating EDS by type

```bash
# Management events EDS
aws cloudtrail create-event-data-store \
  --name "mgmt-eds" \
  --include-management-events \
  --retention-period 90

# Data events EDS (no management events)
aws cloudtrail create-event-data-store \
  --name "data-eds" \
  --no-include-management-events \
  --retention-period 365

# Then add advanced selectors for data events
aws cloudtrail put-event-selectors \
  --event-data-store "<data-eds-id>" \
  --advanced-event-selectors '[...]'
```

## Advanced event selectors

### S3 data events

```bash
aws cloudtrail put-event-selectors \
  --event-data-store "$DATA_EDS_ID" \
  --advanced-event-selectors '[
    {
      "Name": "S3 audit bucket",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
        {"Field": "resources.ARN", "StartsWith": ["arn:aws:s3:::audit-bucket/"]},
        {"Field": "eventName", "Equals": ["PutObject", "DeleteObject"]}
      ]
    }
  ]'
```

### Lambda data events

```bash
aws cloudtrail put-event-selectors \
  --event-data-store "$DATA_EDS_ID" \
  --advanced-event-selectors '[
    {
      "Name": "Lambda invoke events",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::Lambda::Function"]},
        {"Field": "eventName", "Equals": ["Invoke"]}
      ]
    }
  ]'
```

### DynamoDB data events

```bash
aws cloudtrail put-event-selectors \
  --event-data-store "$DATA_EDS_ID" \
  --advanced-event-selectors '[
    {
      "Name": "DynamoDB events",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Data"]},
        {"Field": "resources.type", "Equals": ["AWS::DynamoDB::Table"]},
        {"Field": "resources.ARN", "StartsWith": ["arn:aws:dynamodb:us-east-1:123456789012:table/sensitive-"]}
      ]
    }
  ]'
```

### Cost impact of selectors

| Selector Scope | Example Volume | Monthly Ingestion Cost |
|---|---|---|
| All S3 GetObject (all buckets) | ~100 GB/month | ~$75/month |
| S3 GetObject on 1 bucket | ~1 GB/month | ~$0.75/month |
| S3 PutObject + DeleteObject (1 bucket) | ~0.1 GB/month | ~$0.08/month |
| All Lambda Invoke | ~50 GB/month | ~$37.50/month |
| All DynamoDB GetItem | ~200 GB/month | ~$150/month |

**Key implication:** broad selectors are expensive. Always narrow to
specific resources and event names.

## Multi-account Organization EDS

### Creating an Organization EDS

```bash
ORG_EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "org-mgmt-eds" \
  --include-management-events \
  --organization-enabled \
  --retention-period 2555 \
  --query 'EventDataStoreArn' --output text)
```

The `--organization-enabled` flag:
- Ingests management events from ALL member accounts
- Requires the calling account to be the Organizations management
  account or a delegated administrator
- Events include the `awsAccountId` field for per-account querying

### Querying across accounts

```sql
SELECT
  awsAccountId,
  userIdentity.arn,
  eventName,
  eventTime,
  sourceIPAddress
FROM <org-eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND eventName = 'DeleteBucket'
ORDER BY eventTime DESC
```

### Per-account filtering

```sql
SELECT eventName, eventTime, userIdentity.arn
FROM <org-eds-id>
WHERE eventTime > '2026-08-10T00:00:00Z'
  AND awsAccountId = '123456789012'
ORDER BY eventTime DESC
```

## Retention management

### Setting retention

```bash
# At creation
aws cloudtrail create-event-data-store \
  --name "eds-90day" \
  --include-management-events \
  --retention-period 90

# Update existing EDS
aws cloudtrail update-event-data-store \
  --event-data-store "$EDS_ID" \
  --retention-period 180
```

### Retention range and compliance

| Retention | Compliance Fit |
|---|---|
| 7 days (minimum) | Short-term investigation |
| 90 days | Operational auditing |
| 365 days (1 year) | SOC 2, general compliance |
| 2555 days (7 years) | SOX, financial regulations |
| 3653 days (10 years, maximum) | Long-term regulatory archival |

## Data protection policy

### How PII masking works

Data protection policies apply at the EDS level. When a policy masks
a field, ALL queries against that EDS return masked values. The
original values are not retrievable via the query API.

```bash
aws cloudtrail put-data-protection-policy \
  --event-data-store "$EDS_ID" \
  --policy-document '{
    "Configuration": {
      "Mode": "Mask",
      "MaskingStyle": "REPLACE_WITH_MASK"
    },
    "Identifiers": [
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/EmailAddress",
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/PhoneNumber",
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/AwsSecretKey"
    ]
  }'
```

### Available data identifiers

| Identifier | What it masks |
|---|---|
| EmailAddress | email@domain.com patterns |
| PhoneNumber | International phone patterns |
| AwsSecretKey | AKIA... key patterns |
| CreditCard | Credit card numbers |
| Iban | IBAN codes |
| driversLicense | US driver's license patterns |
| Passport | Passport number patterns |

### Removing data protection

```bash
# Remove the policy (unmasks future queries)
aws cloudtrail delete-data-protection-policy \
  --event-data-store "$EDS_ID"
```

Note: events ingested WHILE the policy was active remain masked at
the storage level. Only new queries after removal see unmasked data
for new events.

## Athena federation

CloudTrail Lake EDS can be queried via Athena for integration with
BI tools and complex analytical queries.

```bash
# Enable Lake Formation resource link
aws lakeformation register-resource \
  --resource-arn "$EDS_ID"

# Create resource link in Athena
aws lakeformation create-resource-link \
  --resource-arn "$EDS_ID" \
  --name "cloudtrail_eds_link"
```

After registration, Athena can query the EDS:

```sql
-- In Athena
SELECT eventName, eventTime, userIdentity.arn
FROM cloudtrail_eds_link
WHERE eventTime > DATE '2026-08-10'
ORDER BY eventTime DESC
```

Athena federation uses the same per-GB scanned billing model.
