# Report Templates and Compliance Frameworks — Backup Audit Automator

Deep reference on the three AWS Backup report templates (content,
format, use cases), compliance framework mapping (CIS, NIST, SOC2
control IDs), and report delivery configuration. Loaded on demand by
the skill — kept out of the main SKILL.md body so the automation
procedure stays scannable.

## Report template details

### BACKUP_JOB_REPORT

Reports on the status of backup jobs (succeeded, failed, aborted).

**Content per row:**
- Backup job ID
- Resource type (e.g., EBS, RDS, EC2, DynamoDB)
- Resource ARN
- Backup vault name
- Job state (COMPLETED, FAILED, ABORTED)
- Start time, completion time, duration
- Error message (if failed)

**Use case:** operational health monitoring — are backups running
successfully?

```bash
aws backup create-report-plan \
  --report-plan-name "backup-job-report" \
  --report-setting '{"ReportTemplate":"BACKUP_JOB_REPORT","Frameworks":[]}' \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/jobs/"}'
```

### COMPLIANCE_REPORT

Reports on which resources are covered by backup plans and which are
NOT. This is the most important report for auditors.

**Content per row:**
- Resource ARN
- Resource type
- Backup plan name (if covered)
- Coverage status (COVERED, NOT_COVERED)
- Region
- Account ID

**Use case:** compliance gap analysis — identify resources without
backup coverage.

```bash
aws backup create-report-plan \
  --report-plan-name "compliance-report" \
  --report-setting '{"ReportTemplate":"COMPLIANCE_REPORT","Frameworks":["CIS_AWS_1.4"]}' \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/compliance/"}'
```

### RECOVERY_POINT_REPORT

Reports on recovery point details including encryption status.

**Content per row:**
- Recovery point ARN
- Backup vault name
- Resource type
- Creation date
- Expiry date (deletion after days)
- Encryption key ARN (KMS key, if present)
- Status (AVAILABLE, DELETED, EXPIRED)
- Size (bytes)

**Use case:** recovery point audit — verify encryption, retention,
and status of all recovery points.

```bash
aws backup create-report-plan \
  --report-plan-name "recovery-point-report" \
  --report-setting '{"ReportTemplate":"RECOVERY_POINT_REPORT","Frameworks":[]}' \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/recovery-points/"}'
```

## Report format and delivery

Reports are delivered as CSV or JSON files to the specified S3 prefix.
File naming convention:

```text
s3://bucket/prefix/template_name_YYYY-MM-DD_HH-MM-SS.csv
```

Example:
```text
s3://backup-reports-bucket/reports/compliance/COMPLIANCE_REPORT_2026-08-11_03-00-00.csv
```

## Compliance framework mapping

### CIS AWS Foundations Benchmark 1.4

| Control | Description | Backup audit check |
|---|---|---|
| 3.5 | Ensure S3 buckets are covered by backup plans | COMPLIANCE_REPORT: S3 resources with coverage |
| 3.7 | Ensure EBS volumes are covered by backup plans | COMPLIANCE_REPORT: EBS resources with coverage |

### NIST 800-53

| Control | Description | Backup audit check |
|---|---|---|
| CP-9 | System backup | All resources covered by backup plans |
| CP-10 | System recovery and reconstitution | Recovery points available and unexpired |
| SC-28 | Protection of information at rest | Recovery points encrypted with KMS |

### SOC 2

| Control | Description | Backup audit check |
|---|---|---|
| CC9.1 | Availability | Backup jobs succeeding, recovery points available |
| CC6.1 | Security and confidentiality | Recovery points encrypted with KMS |
| A1.2 | Environmental protections | Cross-region replication configured |

### Using framework mapping in report plans

```bash
aws backup create-report-plan \
  --report-plan-name "cis-nist-compliance" \
  --report-setting '{"ReportTemplate":"COMPLIANCE_REPORT","Frameworks":["CIS_AWS_1.4","NIST_800_53"]}' \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/cis-nist/"}'
```

The framework mapping adds framework-specific annotations to the
report, making it easier to demonstrate compliance during audits.

## Terraform examples

```hcl
# S3 bucket for backup reports
resource "aws_s3_bucket" "reports" {
  bucket = "backup-reports-bucket"
}

# Bucket policy for backup delivery
resource "aws_s3_bucket_policy" "reports" {
  bucket = aws_s3_bucket.reports.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "backup.amazonaws.com" }
      Action = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.reports.arn}/reports/*"
    }]
  })
}

# Report plan: compliance report
resource "aws_backup_report_plan" "compliance" {
  name = "daily-compliance-report"

  report_setting {
    report_template = "COMPLIANCE_REPORT"
    frameworks      = ["CIS_AWS_1.4"]
  }

  report_delivery_channel {
    s3_bucket_name = aws_s3_bucket.reports.bucket
    s3_key_prefix  = "reports/compliance/"
  }
}

# Report plan: backup job report
resource "aws_backup_report_plan" "jobs" {
  name = "daily-job-report"

  report_setting {
    report_template = "BACKUP_JOB_REPORT"
  }

  report_delivery_channel {
    s3_bucket_name = aws_s3_bucket.reports.bucket
    s3_key_prefix  = "reports/jobs/"
  }
}

# Report plan: recovery point report
resource "aws_backup_report_plan" "recovery_points" {
  name = "daily-recovery-point-report"

  report_setting {
    report_template = "RECOVERY_POINT_REPORT"
  }

  report_delivery_channel {
    s3_bucket_name = aws_s3_bucket.reports.bucket
    s3_key_prefix  = "reports/recovery-points/"
  }
}
```
