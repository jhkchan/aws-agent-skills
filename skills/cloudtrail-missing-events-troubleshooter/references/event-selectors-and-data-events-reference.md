# Event Selectors and Data Events Reference Guide

Supplementary reference for the CloudTrail Missing Events
Troubleshooter skill. Loaded on-demand when a diagnostic needs
event-selector configuration, data-event opt-in rules,
ReadWriteType semantics, advanced event selectors, or
CloudTrail Insights selector configuration.

## Event selector types

CloudTrail supports two event selector types:

| Type | When to use | Configuration |
|---|---|---|
| Basic event selectors (`EventSelectors`) | Simple use cases — all management events, optional S3/Lambda data events | `ReadWriteType`, `IncludeManagementEvents`, `DataResources` |
| Advanced event selectors (`AdvancedEventSelectors`) | Complex use cases — exclude specific event sources, scoped data events, DynamoDB / S3 Object Lambda / other data sources | List of `{Field, Equals, StartsWith, EndsWith, NotEquals, ...}` conditions |

A trail can have one type OR the other, not both. Mixing basic and
advanced selectors on the same trail is not supported.

## Management events

Management events are the control-plane API calls — every
`Create*`, `Delete*`, `Describe*`, `List*`, `Get*`, `Put*` call on
every AWS service that integrates with CloudTrail. They are
**default-on** for any trail with `IncludeManagementEvents: true`.

| Setting | Default | Effect |
|---|---|---|
| `IncludeManagementEvents` | true | If false, no management events are captured at all (rare; usually a misconfiguration). |
| `ReadWriteType: All` | default | Captures both read-type (List*, Describe*, Get*) and write-type (Create*, Put*, Delete*) management events. |
| `ReadWriteType: ReadOnly` | off by default | Captures only List*, Describe*, Get*. Write events (CreateBucket, PutObject, RunInstances) are excluded. |
| `ReadWriteType: WriteOnly` | off by default | Captures only Create*, Put*, Delete*. Read events are excluded. |
| `ExcludeManagementEventSources` | empty | List of event source ARNs to exclude (e.g., `kms.amazonaws.com` to suppress KMS Decrypt noise). |

### Global service events

IAM, STS, and CloudFront deliver events from us-east-1 only, even
when the API call originates from another region. The trail field
`IncludeGlobalServiceEvents` controls whether these events are
captured.

| Setting | Default | Effect |
|---|---|---|
| `IncludeGlobalServiceEvents: true` | default | Captures IAM CreateUser, STS AssumeRole, CloudFront distribution changes from us-east-1. |
| `IncludeGlobalServiceEvents: false` | off | Excludes IAM, STS, CloudFront events. |

Note: `IncludeGlobalServiceEvents` requires the trail to be in
us-east-1 OR to be a multi-region trail with home region us-east-1.
A multi-region trail in a non-us-east-1 home region still captures
global service events only if the home region is us-east-1.

## Data events (the opt-in trap)

Data events are the data-plane API calls — S3 GetObject, Lambda
InvokeFunction, DynamoDB GetItem, and similar. They are **opt-in**;
the default event selector captures ZERO data-plane events.

| Data source | Required event selector | Notes |
|---|---|---|
| S3 GetObject / PutObject / DeleteObject | `DataResources: [{ Type: "AWS::S3::Object", Values: ["arn:aws:s3:::<bucket>/"] }]` | Trailing slash in the ARN matters. Use `arn:aws:s3:::` (no bucket) for all buckets. |
| Lambda InvokeFunction | `DataResources: [{ Type: "AWS::Lambda::Function", Values: ["arn:aws:lambda"] }]` | Captures InvokeFunction only (not the management-plane CreateFunction). |
| DynamoDB GetItem / PutItem / DeleteItem | Advanced event selector with `eventCategory: "Data"` and `resources.type: "AWS::DynamoDB::Table"` | Basic event selectors do NOT support DynamoDB data events. |
| S3 Object Lambda | Advanced event selector with `resources.type: "AWS::S3ObjectLambda::AccessPoint"` | |
| CloudTrail Insights | `list-insights-selectors` / `put-insight-selectors` with `insightsTypes` | Separate selector; not part of the event selector. |
| Glue | `resources.type: "AWS::Glue::Table"` (advanced selector) | Available 2024+. |

### S3 data event ARN patterns

```json
// All buckets, all objects
"Values": ["arn:aws:s3:::"]

// Specific bucket, all objects (trailing slash matters)
"Values": ["arn:aws:s3:::my-bucket/"]

// Specific bucket, specific prefix
"Values": ["arn:aws:s3:::my-bucket/logs/"]
```

A common mistake is omitting the trailing slash —
`arn:aws:s3:::my-bucket` (no slash) captures the bucket-level
events but not object-level events.

### DynamoDB data event selector (advanced)

```json
{
  "AdvancedEventSelectors": [
    {
      "Name": "DynamoDB data events for table-x",
      "FieldSelectors": [
        { "Field": "eventCategory", "Equals": ["Data"] },
        { "Field": "resources.type", "Equals": ["AWS::DynamoDB::Table"] },
        { "Field": "resources.ARN", "Equals": ["arn:aws:dynamodb:us-east-1:111111111111:table/table-x"] }
      ]
    }
  ]
}
```

## CloudTrail Insights

CloudTrail Insights analyses management events to detect anomalous
write activity (unusual API call volume, unusual IAM changes). It
is configured via separate selectors (`put-insight-selectors`).

| Setting | Default | Effect |
|---|---|---|
| `InsightsEnabled` | false on trail creation | Set via `put-insight-selectors`. |
| `InsightsType: ApiCallRateInsight` | default | Detects anomalous API call volume. |
| `InsightsType: ApiErrorRateInsight` | optional | Detects anomalous API error rate. |

Insights requires the trail to have at least 7 days of baseline
events before the first Insight can fire. Operators who "enabled
Insights yesterday and see no findings" are still in the baseline
window.

## CloudTrail Lake event data stores (EDS)

CloudTrail Lake ingests events directly into CloudTrail (no S3 hop)
and supports SQL queries via `start-query`. An EDS has its own
event selectors that are **independent of any S3 trail's selectors**.

```bash
aws cloudtrail list-event-data-stores --output json
aws cloudtrail get-event-selectors --event-data-store <eds-id> --output json
```

| EDS field | Default | Effect |
|---|---|---|
| `eventCategory: Management` | default | Ingests management events only. |
| `eventCategory: Data` | optional | Ingests data events (requires `resources.type`). |
| `eventCategory: Insight` | optional | Ingests Insight findings (requires an Insights-enabled trail). |
| `accounts` (advanced selector) | all accounts in the org | Scope the EDS to specific accounts. |
| `billingMode: EXTENDABLE_RETENTION_PRICING` | default | Lower ingest cost, higher storage cost. |
| `billingMode: PRICE-per-QUERY` | optional | Higher ingest cost, no storage cost. |

Common EDS issues:

- EDS configured with `eventCategory: Management` only; operator
  expects data events (GetObject) but the EDS does not ingest them.
- EDS scoped to a subset of accounts; operator querying for an
  event in an account outside the scope.
- EDS in a different region than the events being queried; Lake is
  regional.
- EDS billing mode `PRICE-per-QUERY` with no query budget; queries
  are throttled.

## ReadWriteType pitfalls

| Setting | Captures | Misses |
|---|---|---|
| `All` | Everything | Nothing |
| `ReadOnly` | ListBuckets, GetObject, DescribeInstances | CreateBucket, PutObject, RunInstances |
| `WriteOnly` | CreateBucket, PutObject, RunInstances | ListBuckets, GetObject, DescribeInstances |

`ReadWriteType: ReadOnly` is the second most common
missing-events cause after data events being opt-in. Operators
debugging "where did the CreateBucket call go" will not find it
under `ReadOnly`.

## Recent AWS features (2024-2026)

- **CloudTrail Lake federated queries (2024-2025):** Lake EDS now
  supports federated queries from Athena, Redshift, and other
  services via the CloudTrail Lake query API. Diagnostically, an
  operator who runs Athena queries against the S3 bucket and
  expects the same results from Lake is comparing two different
  ingestion paths.
- **Advanced event selectors for Glue and Bedrock (2024-2025):**
  Data events for Glue table-level access and Bedrock InvokeModel
  are supported via advanced event selectors. Operators expecting
  these events in a basic event selector will not find them.
- **CloudTrail Lake 365-day retention default (2024):** New EDS
  default retention is 365 days (was 90 days). Older EDS may still
  have shorter retention; queries beyond retention return empty.
- **Organizations delegated administrator for CloudTrail (2024):**
  The delegated administrator account can manage org trails; the
  management account retains the cloudtrail:UpdateTrail permission.
  Operators who "cannot update the org trail from the member
  account" are hitting this delegation.
- **CloudTrail error-rate Insights default-on (2025):** New trails
  created in 2025 default to Insights enabled with both
  ApiCallRateInsight and ApiErrorRateInsight. Older trails still
  require explicit `put-insight-selectors`.

## AWS documentation references

- CloudTrail event selectors: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-management-and-data-events-with-cloudtrail.html
- CloudTrail Insights: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-insights-events-with-cloudtrail.html
- CloudTrail Lake: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
- S3 data events: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html

## Canonical data-event selector configurations (Step 4)

Data events require an event selector with `DataResources`
configured. The canonical configurations:

| Data source | Required event selector |
|---|---|
| S3 GetObject / PutObject / DeleteObject | `DataResources: [{ Type: "AWS::S3::Object", Values: ["arn:aws:s3:::<bucket>/"] }]` (trailing slash matters) |
| Lambda InvokeFunction | `DataResources: [{ Type: "AWS::Lambda::Function", Values: ["arn:aws:lambda"] }]` |
| DynamoDB GetItem / PutItem / DeleteItem | `DataResources: [{ Type: "AWS::DynamoDB::Stream", Values: ["arn:aws:dynamodb"] }]` (advanced event selector recommended) |

To enable S3 data events for a specific bucket:

```bash
aws cloudtrail put-event-selectors --trail-name <trail> \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{ "Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::<bucket>/"] }]
  }]'
```
