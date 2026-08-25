# Output Location and Compliance — SSM Association Operator

Deep reference on association output routing (S3 output location, KMS
encryption requirements, bucket policy, prefix structure, lifecycle
rules), compliance reporting (ComplianceType=Association, status
mechanics, NON_COMPLIANT triggers, drift detection timeline), and
remediation patterns (manual StartAssociationsOnce, EventBridge-driven
auto-remediation, idempotency requirements). Loaded on demand by the
skill — kept out of the main SKILL.md body so the operating procedure
stays scannable.

## Output location fundamentals

### Where execution artifacts go

When an association runs a document on a target instance, SSM captures
the execution artifacts (stdout, stderr, script payloads, plugin
output). These artifacts are delivered to the S3 bucket specified in
`--output-location`.

```text
Execution artifacts layout:
  s3://<bucket>/<prefix>/<association-id>/<execution-id>/<instance-id>/
    ├── <plugin-name>/
    │   ├── stdout
    │   ├── stderr
    │   └── output.json
    └── ...
```

**Configure output location:**

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --output-location '{
    "S3Location": {
      "OutputS3BucketName": "my-ssm-output",
      "OutputS3KeyPrefix": "ssm-output/",
      "OutputS3Region": "us-east-1"
    }
  }' \
  --region us-east-1
```

If `--output-location` is omitted, SSM stores execution output only
in the response to `describe-association-execution-targets` (truncated
at 2500 characters). For any production use, ALWAYS specify an S3
output location.

### Why the bucket needs KMS-encrypted SSE

Execution artifacts can contain:
- Stdout from scripts (which may include secrets, environment
  variables, configuration values)
- Stderr with stack traces (which may include sensitive paths, IAM
  principal ARNs, internal hostnames)
- Plugin output (which may include inventory of installed packages,
  user lists, network configuration)

Shipping these to an unencrypted S3 bucket is a security finding.
SSM does NOT enforce SSE on the output bucket; the operator must
configure it.

**SSE options for the output bucket:**

| Option | Key manager | Recommended | Notes |
|---|---|---|---|
| SSE-KMS (customer-managed key) | You | Yes — production | Most control; per-bucket key; auditable via CloudTrail |
| SSE-KMS (AWS-managed key) | AWS | Acceptable | Easier; shared `aws/s3` key; less granular audit |
| SSE-S3 (S3-managed keys) | S3 | No — flagged | No per-key control; not visible in KMS console |
| No encryption | n/a | Never | Finding |

**The skill flags SSE-S3 buckets as REVIEW_REQUIRED.** SSE-S3 is
technically encrypted at rest, but it lacks the per-key control and
CloudTrail visibility that customer-managed KMS provides. For
production execution artifacts that may contain secrets, always use
SSE-KMS with a customer-managed key.

### Verifying the bucket's encryption

```bash
# Check bucket encryption configuration
aws s3api get-bucket-encryption --bucket my-ssm-output --region us-east-1

# Expected for SSE-KMS (customer-managed):
# {
#   "ServerSideEncryptionConfiguration": {
#     "Rules": [{
#       "ApplyServerSideEncryptionByDefault": {
#         "SSEAlgorithm": "aws:kms",
#         "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789012:key/abc123"
#       }
#     }]
#   }
# }

# If the response is empty or shows "AES256" (SSE-S3), the bucket
# lacks a customer-managed KMS key → REVIEW_REQUIRED.
```

### Bucket policy

The SSM service principal must have `s3:PutObject` permission on the
output prefix. The bucket policy is the cleanest place to grant this.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-ssm-output/ssm-output/*"
    }
  ]
}
```

**For SSE-KMS buckets**, the KMS key policy must also allow the SSM
service principal to `kms:GenerateDataKey`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      "Resource": "*"
    }
  ]
}
```

Without the KMS key policy grant, SSM silently drops output. The
association still runs, but no artifacts are delivered.

**Silent-drop verification:** check CloudTrail for `AccessDenied`
events from `ssm.amazonaws.com` against the KMS key or S3 bucket. If
present, the policies are incomplete.

### Prefix structure and lifecycle

A flat output prefix becomes hard to query over time. Use a per-
association prefix structure:

```text
s3://my-ssm-output/ssm-output/
  ├── a-1a2b3c4d5e6f7g8h9/                # association ID
  │   ├── $EXECUTION_ID_1/
  │   │   ├── i-aaa111bb222/
  │   │   └── i-ccc333dd444/
  │   └── $EXECUTION_ID_2/
  │       └── ...
  └── a-2b3c4d5e6f7g8h9i0/
      └── ...
```

Apply an S3 lifecycle rule to transition older execution output to
cheaper storage tiers or expire it:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-ssm-output \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "ExpireSSMOutput",
      "Filter": {"Prefix": "ssm-output/"},
      "Status": "Enabled",
      "Expiration": {"Days": 90},
      "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]
    }]
  }'
```

90-day retention is a reasonable default for debugging; adjust based
on audit requirements.

## Compliance reporting

### ComplianceType=Association

SSM compliance reports include several ComplianceTypes. The most
relevant for State Manager associations is `Association`.

```bash
# List all compliance items of type Association
aws ssm list-compliance-items \
  --filters "Key=ComplianceType,Values=Association" \
  --region us-east-1

# Aggregate compliance summary per resource
aws ssm list-resource-compliance-summaries \
  --filters "Key=ComplianceType,Values=Association" \
  --region us-east-1
```

### Compliance status values

| Status | Meaning | Action |
|---|---|---|
| `COMPLIANT` | Last association execution was Successful | None |
| `NON_COMPLIANT` | Last association execution Failed, or drift detected | Investigate, remediate |
| `PENDING` | Association created but never executed | Wait for first run, or trigger with StartAssociationsOnce |

**Critical:** a resource's compliance status is computed only AFTER
the first association execution that targets it. Before the first
execution, the resource shows no compliance item at all (not even
`PENDING` — `PENDING` appears only after the first execution attempt
that has not yet completed).

### Compliance state change events

SSM emits an EventBridge event whenever a resource's compliance state
changes. This is the basis for auto-remediation.

```json
{
  "source": ["aws.ssm"],
  "detail-type": ["Configuration Compliance State Change"],
  "detail": {
    "status": ["NON_COMPLIANT"]
  }
}
```

Subscribe to this event pattern to trigger remediation, send a
notification, or open a ticket.

## Remediation patterns

### Pattern 1: manual StartAssociationsOnce

For immediate one-off remediation, trigger the association manually.

```bash
aws ssm start-associations-once \
  --association-ids "a-1a2b3c4d5e6f7g8h9" \
  --region us-east-1
```

This triggers an immediate run of the association, regardless of its
schedule. Use this for incident response.

### Pattern 2: EventBridge → SSM Automation (auto-remediation)

The most production-grade pattern. EventBridge matches the compliance
state change event and triggers an SSM Automation document that calls
`StartAssociationsOnce` on the relevant association.

```text
NON_COMPLIANT detected
  → EventBridge rule matches
  → Target: SSM Automation (AWS-StartAssociation)
  → Input: association-id from the event detail
  → SSM re-applies the document
  → Compliance flips back to COMPLIANT (if the document succeeded)
```

**EventBridge rule:**

```bash
aws events put-rule \
  --name "ssm-association-remediation" \
  --event-pattern '{
    "source": ["aws.ssm"],
    "detail-type": ["Configuration Compliance State Change"],
    "detail": {"status": ["NON_COMPLIANT"]}
  }'
```

**Target: SSM Automation (StartAssociationsOnce)**

Use an SSM Automation document that wraps `aws:ssm:startAssociation`
(or a custom Lambda-backed Automation). Provide the association-id
from the event detail as the input.

### Pattern 3: EventBridge → Lambda (custom logic)

For more control (filtering by association, by severity, by account),
route the event to a Lambda function that decides whether to
remediate.

```python
import boto3, json

ssm = boto3.client('ssm')

def lambda_handler(event, context):
    detail = event.get('detail', {})
    association_id = detail.get('association-id')
    severity = detail.get('severity', 'MEDIUM')

    # Only auto-remediate HIGH severity, specific associations
    if severity == 'HIGH' and association_id in {'a-1a2b3c4d5e6f7g8h9'}:
        ssm.start_associations_once(AssociationIds=[association_id])
        return {'statusCode': 200, 'body': f'Remediated {association_id}'}

    return {'statusCode': 200, 'body': 'No action'}
```

### Idempotency — the non-negotiable prerequisite

ALL remediation patterns re-apply the document. If the document is
not idempotent (e.g., it appends a line to a file, increments a
counter, or creates a unique resource each run), remediation will
cause side effects.

**Idempotent documents are safe to re-run.** Examples:
- `AWS-ApplyPatchBaseline` (installs missing patches; no-op if
  already installed)
- `AWS-GatherSoftwareInventory` (read-only)
- A custom document that uses `assert`/`apply` semantics (check if
  the state is correct; if so, no-op; if not, apply the desired state)

**Non-idempotent documents are NOT safe to remediate.** Examples:
- A document that appends a line to `/etc/hosts` (each run adds a
  duplicate line)
- A document that creates a new IAM user with a unique name
- A document that increments a metric counter

Before wiring remediation, audit the document body. The skill asks
the user to confirm idempotency before emitting the remediation
configuration.

## Common compliance pitfalls

### Pitfall 1: compliance shows NON_COMPLIANT but last run was Success

This can happen when the association includes a compliance check step
(a `aws:assert` or similar) that detected drift after the successful
run. For example, a patch association installed patches successfully
but a later compliance scan detected a missing kernel update.

**Fix:** inspect the compliance item details:

```bash
aws ssm list-compliance-items \
  --resource-ids "i-aaa111bb222" \
  --filters "Key=ComplianceType,Values=Association" \
  --region us-east-1
```

The `DocumentName` and `Severity` fields indicate which document
flagged the drift.

### Pitfall 2: compliance never updates

If the association schedule is too sparse (e.g., `cron(0 0 1 ? * *)`
— once a month), compliance status may be stale for weeks. The
compliance status reflects the LAST execution; sparse schedules mean
slow drift detection.

**Fix:** for compliance-critical associations, use a more frequent
schedule (`rate(30 minutes)` or `rate(1 hour)`).

### Pitfall 3: remediation triggers infinitely

If the document itself causes non-compliance (e.g., a bug), the
remediation loop fires indefinitely: NON_COMPLIANT → remediation →
NON_COMPLIANT → remediation → ...

**Fix:** add a circuit breaker in the Lambda function (pattern 3) to
cap remediation attempts per association per hour. Alternatively, use
a dead-letter queue on the EventBridge target to capture failed
remediations.

## Terraform example: output with KMS and lifecycle

```hcl
resource "aws_ssm_association" "patch_production" {
  name = "AWS-ApplyPatchBaseline"

  targets {
    key    = "tag:Environment"
    values = ["production"]
  }

  schedule_expression = "rate(30 minutes)"

  output_location {
    s3_bucket_name = aws_s3_bucket.ssm_output.bucket
    s3_key_prefix  = "ssm-output/"
    s3_region      = "us-east-1"
  }

  apply_only_at_cron_interval = false
}

resource "aws_s3_bucket" "ssm_output" {
  bucket = "my-ssm-output"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ssm_output" {
  bucket = aws_s3_bucket.ssm_output.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.ssm_output.arn
    }
  }
}

resource "aws_kms_key" "ssm_output" {
  description             = "KMS key for SSM output bucket"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_s3_bucket_lifecycle_configuration" "ssm_output" {
  bucket = aws_s3_bucket.ssm_output.id

  rule {
    id     = "expire-ssm-output"
    status = "Enabled"

    filter {
      prefix = "ssm-output/"
    }

    expiration {
      days = 90
    }
  }
}
```

## Expert heuristic: S3 output bucket encryption

SSM execution output (stdout, stderr, script payloads) can contain
sensitive data. The output bucket MUST have SSE enabled, and for
production that means a customer-managed KMS key.

```text
Output S3 bucket:
  ├── Bucket exists
  │     aws s3api head-bucket --bucket my-ssm-output
  ├── SSE enabled (KMS preferred over SSE-S3)
  │     customer-managed KMS key: kms-key-arn
  │     bucket policy allows ssm: s3:PutObject
  │     KMS key policy allows ssm: kms:GenerateDataKey
  └── Without KMS → REVIEW_REQUIRED (silent security finding)
```

**Key implication:** SSM does not enforce SSE. An unencrypted bucket
is a silent finding. The skill flags any output bucket without a KMS
key.
