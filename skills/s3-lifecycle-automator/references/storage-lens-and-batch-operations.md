# Storage Lens and Batch Operations Reference

Supplementary reference for the S3 Lifecycle Automator skill. Use when
identifying lifecycle gaps via Storage Lens, designing multi-account
lifecycle enforcement, or running S3 Batch Operations for retroactive
storage-class tiering.

## Storage Lens for lifecycle audit

Storage Lens provides organization-wide storage metrics. The lifecycle-
relevant metrics are:

| Metric | What it reveals | Lifecycle action |
|---|---|---|
| `LifecycleEnabled` (count) | Buckets with/without lifecycle policy | Deploy to buckets where `false` |
| `StorageClass` distribution | Objects by storage class | If 90%+ in Standard, lifecycle missing or ineffective |
| `ObjectAge` distribution | Objects by age bucket (0-30d, 31-90d, 91-180d, 180d+) | Drives transition day selection |
| `NoncurrentVersionStorage` | Bytes consumed by non-current versions | Drives NoncurrentVersionExpiration |
| `IncompleteMultipartUploadStorage` | Bytes from orphaned multipart uploads | Add AbortIncompleteMultipartUpload |
| `BucketCount` | Total bucket count | Denominator for coverage ratio |

### Storage Lens configuration levels

| Level | Metrics available | Cost |
|---|---|---|
| Default (free) | Basic metrics (bucket count, storage, object count) | Free |
| Advanced (paid) | All metrics including lifecycle, storage class, object age | $0.20 per million objects monitored/month |
| Organization-level | All advanced metrics aggregated across all accounts | Paid; requires organization-level config |

### Enable organization-level Storage Lens

```bash
aws s3control put-storage-lens-configuration \
  --config-id org-storage-lens \
  --account-id 111111111111 \
  --storage-lens-configuration '{
    "Id": "org-storage-lens",
    "StorageLensArn": "",
    "AwsOrg": {"Arn": "arn:aws:organizations:111111111111:organization/o-xxxxxxx"},
    "StorageLensConfiguration": {
      "IsEnabled": true,
      "AccountLevel": {
        "BucketLevel": {
          "ActivityMetrics": {"IsEnabled": true},
          "AdvancedCostOptimizationMetrics": {"IsEnabled": true},
          "DetailedStatusCodesMetrics": {"IsEnabled": true}
        }
      },
      "Features": {
        "BucketLevel": {
          "StorageClassDistribution": {"IsEnabled": true},
          "ObjectAgeDistribution": {"IsEnabled": true}
        }
      }
    }
  }'
```

### Query Storage Lens findings

```bash
aws s3control get-storage-lens-configuration \
  --config-id org-storage-lens \
  --account-id 111111111111

# Export the report to S3 for analysis
aws s3control get-storage-lens-configuration-tagging \
  --config-id org-storage-lens \
  --account-id 111111111111
```

The Storage Lens dashboard (S3 console) shows the `LifecycleEnabled`
count directly. For API/CLI-based automation, export the daily CSV
report and parse for buckets with `LifecycleEnabled=false`.

## S3 Batch Operations for retroactive tiering

Lifecycle policies apply prospectively. For existing objects that need
immediate storage-class changes, use Batch Operations.

### Job creation

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3SetStorageClass": {"TargetStorageClass": "GLACIER_IR"}}' \
  --report '{
    "Bucket": "arn:aws:s3:::batch-ops-reports",
    "Format": "Report_CSV_20180820",
    "Enabled": true,
    "ReportScope": "AllTasks"
  }' \
  --manifest '{
    "Spec": {
      "Format": "S3BatchOperations_CSV_20180820",
      "Fields": ["Bucket", "Key"]
    },
    "Location": {
      "ObjectArn": "arn:aws:s3:::batch-ops-manifests/manifest.csv",
      "ETag": "<etag-of-manifest-csv>"
    }
  }' \
  --priority 10 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsRole \
  --client-request-token "$(uuidgen)"
```

### Generate the manifest

From S3 Inventory (recommended for large buckets):

```bash
# S3 Inventory generates a daily CSV. Use the latest report as the manifest.
aws s3api get-object \
  --bucket inventory-reports \
  --key destination/source-bucket/data/<date>/manifest.json \
  /tmp/inventory-manifest.json
```

From a manual query (for smaller buckets):

```bash
aws s3api list-objects-v2 \
  --bucket my-data-bucket \
  --query 'Contents[?StorageClass==`STANDARD`].[Bucket,Key]' \
  --output text | awk '{print "my-data-bucket," $2}' > manifest.csv
```

### Monitor the job

```bash
aws s3control describe-job \
  --account-id 111111111111 \
  --job-id <job-id> \
  --query 'Job.[Status,ProgressSummary.TotalNumberOfTasks,ProgressSummary.NumberOfTasksSucceeded,ProgressSummary.NumberOfTasksFailed]'
```

### Batch Operations role requirements

The `S3BatchOperationsRole` must have:

1. Trust policy allowing `batchoperations.s3.amazonaws.com` to assume it.
2. `s3:GetObject`, `s3:PutObject` (or `s3:ReplicateObject`) on target buckets.
3. `s3:GetObject` on the manifest bucket.
4. `s3:PutObject` on the report bucket.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::target-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::batch-ops-manifests/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::batch-ops-reports/*"
    }
  ]
}
```

### Batch Operations safety checklist

| Check | Why |
|---|---|
| Test on 10 objects first | Verify storage class change before full run |
| Enable reporting | Audit trail of success/failure per object |
| Use `ReportScope: AllTasks` | Include both succeeded and failed tasks in report |
| Set `Priority` appropriately | Higher priority jobs preempt lower |
| Monitor `NumberOfTasksFailed` | Failures indicate permission or object-access issues |
| Verify manifest ETag | Stale ETag produces `NoSuchKey` errors |

## Integration pattern

```
Storage Lens → identify lifecycle gaps
    ↓
Design per-bucket lifecycle policy (based on ObjectAge distribution)
    ↓
Validate min-days rules (Step 9 of SKILL.md)
    ↓
Deploy via put-bucket-lifecycle-configuration (single) or StackSets (multi-account)
    ↓
S3 Batch Operations for existing objects that need immediate tiering
    ↓
EventBridge monitoring for policy changes
    ↓
Storage Lens verification (StorageClass distribution shifts over time)
```

## Multi-account lifecycle enforcement patterns

### Pattern A: CloudFormation StackSets (recommended)

- Pro: Declarative, version-controlled, auto-deploys to new accounts
- Con: Requires StackSet administration role in each account
- Best for: Organization-wide standard lifecycle baselines

### Pattern B: Lambda with tag-based discovery

- Pro: Flexible, can apply different policies by tag
- Con: No audit trail (unless explicitly logged), must handle rate limits
- Best for: Per-bucket customization based on tags

### Pattern C: AWS Config rule + auto-remediation

- Pro: Continuous compliance, auto-remediates drift
- Con: Requires custom Config rule + SSM runbook
- Best for: Enforcing lifecycle as a compliance requirement

Choose StackSets for standard baselines, Lambda for tag-based
customization, and Config for compliance enforcement.

---

### Step 7: Identify lifecycle gaps via Storage Lens


```bash
aws s3control get-storage-lens-configuration \
  --config-id org-storage-lens \
  --account-id 111111111111
```

| Metric | What it reveals | Action |
|---|---|---|
| `LifecycleEnabled` | Buckets with lifecycle policy | Deploy to the gap |
| `StorageClass` distribution | Objects by storage class | If 90%+ Standard, lifecycle missing |
| `ObjectAge` distribution | Objects by age bucket | Drives transition day selection |
| `NoncurrentVersionStorage` | Non-current version storage | Drives NoncurrentVersionExpiration |

---

### Step 8: Retroactive tiering via S3 Batch Operations


```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3SetStorageClass": {"TargetStorageClass": "GLACIER_IR"}}' \
  --report '{"Bucket": "arn:aws:s3:::batch-ops-reports", "Format": "Report_CSV_20180820", "Enabled": true}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820", "Fields": ["Bucket", "Key"]}, "Location": {"ObjectArn": "arn:aws:s3:::batch-ops-manifests/manifest.csv"}}' \
  --priority 10 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsRole
```

Monitor: `aws s3control describe-job --account-id 111111111111 --job-id <id>`
