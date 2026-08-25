# Athena Permission and CTAS Output Location Reference Guide

Supplementary reference for the Athena Query Failure Troubleshooter
skill. Loaded on-demand when a diagnostic needs the two-layer
permission model (Glue + S3), Lake Formation integration, or CTAS
output location detail.

## The two-layer permission model

Athena queries touch TWO independent AWS permission layers:

```
┌─────────────────────────────────────────────────┐
│                  Athena Query                    │
├──────────────────┬──────────────────────────────┤
│  Layer 1: Glue   │  Layer 2: S3                 │
│  Data Catalog    │  Data Bucket                 │
│                  │                              │
│  glue:GetTable   │  s3:GetObject                │
│  glue:GetDatabase│  s3:ListBucket               │
│  glue:GetPartitions│  s3:GetBucketLocation       │
└──────────────────┴──────────────────────────────┘
```

A query fails if EITHER layer denies. The error message tells you
which:

| Error message | Failed layer |
|---|---|
| `is not authorized to perform: glue:GetTable` | Glue Data Catalog (IAM) |
| `Access Denied s3://bucket/path` | S3 data bucket (IAM or bucket policy) |
| `glue:GetTable` works but query fails on S3 read | S3 (Glue passed, S3 denied) |
| `Insufficient permissions to execute the query` | Could be either; check StateChangeReason |

## Glue Data Catalog IAM permissions

### Minimum permissions for a read-only Athena query

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases"
      ],
      "Resource": [
        "arn:aws:glue:<region>:<acct>:catalog",
        "arn:aws:glue:<region>:<acct>:database/<db>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartition",
        "glue:GetPartitions",
        "glue:BatchGetPartition"
      ],
      "Resource": [
        "arn:aws:glue:<region>:<acct>:catalog",
        "arn:aws:glue:<region>:<acct>:database/<db>",
        "arn:aws:glue:<region>:<acct>:table/<db>/<table>"
      ]
    }
  ]
}
```

### For CTAS (CREATE TABLE AS SELECT)

Add:
```json
{
  "Effect": "Allow",
  "Action": [
    "glue:CreateTable",
    "glue:UpdateDatabase",
    "glue:GetTable"
  ],
  "Resource": [
    "arn:aws:glue:<region>:<acct>:catalog",
    "arn:aws:glue:<region>:<acct>:database/<target-db>",
    "arn:aws:glue:<region>:<acct>:table/<target-db>/<new-table>"
  ]
}
```

## S3 IAM permissions

### Minimum for reading data

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:GetObjectVersion"
  ],
  "Resource": "arn:aws:s3:::<data-bucket>/*"
},
{
  "Effect": "Allow",
  "Action": [
    "s3:ListBucket",
    "s3:GetBucketLocation"
  ],
  "Resource": "arn:aws:s3:::<data-bucket>"
}
```

### For writing query results / CTAS output

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:AbortMultipartUpload",
    "s3:GetObject"
  ],
  "Resource": "arn:aws:s3:::<result-bucket>/*"
},
{
  "Effect": "Allow",
  "Action": [
    "s3:GetBucketLocation",
    "s3:ListBucketMultipartUploads",
    "s3:ListMultipartUploadPart"
  ],
  "Resource": "arn:aws:s3:::<result-bucket>"
}
```

### S3 bucket policy interactions

Even if the IAM role has S3 permissions, the bucket policy can still
deny access. Check:

```bash
aws s3api get-bucket-policy --bucket <bucket> --output json --profile <p>
```

A bucket policy with an explicit `Deny` overrides an IAM `Allow`.

### Cross-account S3 access

If the Athena role is in account A and the data bucket is in account B:

1. Account B's bucket policy must grant `s3:GetObject` and
   `s3:ListBucket` to account A's role ARN.
2. Account A's IAM role must have `s3:GetObject` and `s3:ListBucket`
   on account B's bucket.
3. Both sides must allow; either side denying blocks the query.

## Lake Formation integration

If Lake Formation is enabled on the Glue Data Catalog, LF-Tags and
database-level grants override IAM:

### Check Lake Formation permissions

```bash
aws lakeformation list-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> \
  --output json
```

### Grant Lake Formation access

```bash
# Grant SELECT on a specific table
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> \
  --permissions SELECT DESCRIBE \
  --resource '{ "Table": {"DatabaseName": "<db>", "Name": "<table>", "CatalogId": "<acct>"}}'

# Grant via LF-Tag
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> \
  --permissions SELECT DESCRIBE \
  --resource '{ "LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}]}}'
```

### Lake Formation vs IAM

| Scenario | IAM allows | Lake Formation allows | Result |
|---|---|---|---|
| Both allow | Yes | Yes | Access granted |
| IAM denies | No | Yes | Access denied |
| IAM allows | Yes | No | Access denied (LF overrides) |
| Both deny | No | No | Access denied |

**Key rule:** Lake Formation being enabled means IAM Glue permissions
are necessary but NOT sufficient. LF grants must also be present.

## Workgroup result location — detailed rules

### How Athena resolves the query output location

Priority (highest to lowest):

1. **Workgroup OutputLocation** (when
   `EnforceWorkGroupConfiguration=true`): overrides everything.
2. **Client-side output location** (API `ResultConfiguration.OutputLocation`
   parameter): used when `EnforceWorkGroupConfiguration=false`.
3. **Query-level `external_location`** (for CTAS): used when
   `EnforceWorkGroupConfiguration=false` AND no client-side location.

### CTAS-specific behavior

For `CREATE TABLE AS SELECT` with `WITH (external_location = '...')`:

| Workgroup setting | CTAS writes to |
|---|---|
| `EnforceWorkGroupConfiguration=true` | Workgroup OutputLocation (ignores `external_location`) |
| `EnforceWorkGroupConfiguration=false` + `external_location` set | The `external_location` path |
| `EnforceWorkGroupConfiguration=false` + no `external_location` | Workgroup OutputLocation |

### Result location permission check

```bash
# Verify the role can write to the result bucket
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names s3:PutObject s3:AbortMultipartUpload \
  --resource-arns arn:aws:s3:::<result-bucket>/* \
  --output json --profile <p>
```

If `implicitDeny`, add the permissions or change the workgroup result
location to a bucket the role can write to.

## Athena error message reference

| Error category | Typical message | Layer | Diagnostic branch |
|---|---|---|---|
| `SYNTAX_ERROR` | `mismatched input 'X' expecting Y` | SQL | Re-examine query; check engine version |
| `HIVE_BAD_DATA` | `Error parsing field value for field X` | SerDe / format | SERDE_MISMATCH / FORMAT_INFERENCE |
| `HIVE_CURSOR_ERROR` | `Error reading row from file` | SerDe / column type | SERDE_MISMATCH / COLUMN_TYPE_MISMATCH |
| `COLUMN_NOT_FOUND` | `Column 'X' cannot be resolved` | Table definition | TABLE_LOCATION / stale definition |
| `Access Denied` (S3) | `Access Denied s3://...` | S3 permission | S3_PERMISSION / CTAS_OUTPUT_LOCATION |
| `is not authorized: glue:*` | `glue:GetTable is not authorized` | Glue permission | GLUE_PERMISSION |
| `Query exhausted resources` | `at X milliseconds` | Timeout (30 min) | QUERY_TIMEOUT |
| `INSUFFICIENT_RESOURCES` | (workgroup byte limit) | Workgroup limit | Raise cutoff or reduce scan |
| `TABLE_NOT_FOUND` | `Table does not exist` | Glue catalog | Check database/table name |
| `PARTITION_NOT_FOUND` | (no partition metadata) | Partitions | STALE_PARTITIONS / PARTITION_PROJECTION |
| `INVALID_FORMAT` | `Cannot parse date` | Date / type | DATE_PARSE_ERROR / COLUMN_TYPE_MISMATCH |

## Quick troubleshooting flow

```
get-query-execution → Status?
├── SUCCEEDED → wrong data? → glue get-table → SerDe check
├── FAILED → StateChangeReason?
│   ├── Access Denied s3:// → S3_PERMISSION
│   ├── glue:* is not authorized → GLUE_PERMISSION
│   ├── HIVE_BAD_DATA → SERDE_MISMATCH / FORMAT_INFERENCE
│   ├── HIVE_CURSOR_ERROR → COLUMN_TYPE_MISMATCH / SERDE_MISMATCH
│   ├── Query exhausted resources → QUERY_TIMEOUT
│   └── COLUMN_NOT_FOUND → TABLE_LOCATION
└── CANCELLED → near 30 min? → QUERY_TIMEOUT
```

---

## Step 4: S3 and Glue permission (moved from SKILL.md)

Symptom: `Access Denied s3://...` or `glue:GetTable is not authorized`.

#### 4a: S3 permission

```bash
# Check if the IAM role can list and get objects on the data bucket
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names s3:GetObject s3:ListBucket \
  --resource-arns arn:aws:s3:::<bucket> arn:aws:s3:::<bucket>/* \
  --output json --profile <p>
```

The role needs:
- `s3:ListBucket` on `arn:aws:s3:::<bucket>`
- `s3:GetObject` on `arn:aws:s3:::<bucket>/*`

Also check the bucket policy (it can deny even when IAM allows):

```bash
aws s3api get-bucket-policy --bucket <bucket> --output json --profile <p>
```

If the role lacks S3 permissions, ROOT_CAUSE_IDENTIFIED,
`LAYER: S3_PERMISSION`.

#### 4b: Glue Data Catalog permission

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names glue:GetTable glue:GetPartitions glue:GetDatabase \
  --resource-arns arn:aws:glue:<region>:<acct>:catalog \
    arn:aws:glue:<region>:<acct>:database/<db> \
    arn:aws:glue:<region>:<acct>:table/<db>/<table> \
  --output json --profile <p>
```

If the role lacks Glue permissions, ROOT_CAUSE_IDENTIFIED,
`LAYER: GLUE_PERMISSION`.

If the catalog has Lake Formation enabled, also check LF-Tags:

```bash
aws lakeformation list-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> --output json
```

Lake Formation grants override IAM; an IAM allow does not help if Lake
Formation does not grant access.

---

## Step 5: CTAS output location (moved from SKILL.md)

Symptom: `CREATE TABLE AS SELECT` fails with Access Denied.

```bash
aws athena get-work-group --work-group <wg> --output json | \
  jq '.WorkGroup.Configuration.ResultConfiguration.OutputLocation'

aws athena get-work-group --work-group <wg> --output json | \
  jq '.WorkGroup.Configuration.EnforceWorkGroupConfiguration'
```

The CTAS output goes to:
1. The workgroup result location (if
   `EnforceWorkGroupConfiguration: true`) — overrides everything.
2. The `external_location` in the CTAS (if
   `EnforceWorkGroupConfiguration: false`).
3. The client-side output location (if neither is set).

Check the IAM role's permission on the RESULT bucket:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names s3:PutObject s3:AbortMultipartUpload \
  --resource-arns arn:aws:s3:::<result-bucket>/* \
  --output json --profile <p>
```

The role needs `s3:PutObject` on the result bucket. If missing,
ROOT_CAUSE_IDENTIFIED, `LAYER: CTAS_OUTPUT_LOCATION`.

| CTAS failure pattern | Cause |
|---|---|
| Access Denied on workgroup result bucket | Role lacks `s3:PutObject` on the result bucket |
| CTAS writes to unexpected bucket | `EnforceWorkGroupConfiguration: true` overrides `external_location` |
| CTAS table's LOCATION is wrong in Glue | The table LOCATION is set to the actual output path after the write; it will be under the result bucket, not the source table bucket |
| CTAS fails with "Query output location is not set" | Workgroup has no result location configured AND no client-side location provided |

---

## Workgroup configuration matrix (moved from SKILL.md)

| Config | Effect |
|---|---|
| `ResultConfiguration.OutputLocation` | Where query results and CTAS output go |
| `EnforceWorkGroupConfiguration` | `true` = overrides client-side output location; `false` = client can override |
| `BytesScannedCutoffPerQuery` | Query fails if bytes scanned exceeds this; 0 = no limit (use sparingly) |
| `RequesterPaysEnabled` | Allows queries on RequesterPays S3 buckets |
| `EngineVersion.SelectedEngineVersion` | `Athena engine 2` or `Athena engine 3` (Trino); affects function support and type coercion |
| `PublishCloudWatchMetricsEnabled` | Whether query metrics are emitted to CloudWatch |
