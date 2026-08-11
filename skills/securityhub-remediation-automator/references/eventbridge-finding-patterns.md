# Security Hub EventBridge Finding Patterns Reference

Supplementary reference for the Security Hub Remediation Automator skill.
Use when designing EventBridge rules for Security Hub finding automation,
selecting severity filters, or debugging why a rule is not firing.

## EventBridge event structure for Security Hub findings

Security Hub publishes finding events to EventBridge on the default event
bus. The event has three critical fields for routing:

| Field | Value | Purpose |
|---|---|---|
| `source` | `aws.securityhub` | Identifies the event source |
| `detail-type` | `Security Hub Findings - Imported` | Finding ingestion (automation) |
| `detail-type` | `Security Hub Findings - Custom Action` | Human-triggered custom action (manual) |
| `detail.findings[0].Severity.Label` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Severity routing |
| `detail.findings[0].Workflow.Status` | `NEW`, `NOTIFIED`, `RESOLVED`, `SUPPRESSED` | Workflow status filtering |
| `detail.findings[0].RecordState` | `ACTIVE`, `ARCHIVED` | Active vs suppressed |
| `detail.findings[0].Resources[0].Type` | `AwsS3Bucket`, `AwsIamUser`, etc. | Resource type routing |

## Severity-filtered EventBridge rule patterns

### CRITICAL + HIGH auto-remediation rule

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Severity": {"Label": ["CRITICAL", "HIGH"]},
      "Workflow": {"Status": ["NEW"]},
      "RecordState": ["ACTIVE"]
    }
  }
}
```

### MEDIUM notify-only rule

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Severity": {"Label": ["MEDIUM"]},
      "Workflow": {"Status": ["NEW"]}
    }
  }
}
```

### Resource-type-filtered rule (S3 only)

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Resources": {"Type": ["AwsS3Bucket"]},
      "Severity": {"Label": ["CRITICAL", "HIGH"]}
    }
  }
}
```

## Input transformer for Lambda targets

The finding payload is nested at `detail.findings[0]`. Use an input
transformer to extract it:

```json
{
  "InputPathsMap": {
    "finding": "$.detail.findings[0]",
    "account": "$.account",
    "region": "$.region"
  },
  "InputTemplate": "{\"finding\": <finding>, \"account\": <account>, \"region\": <region>}"
}
```

Without the transformer, the Lambda receives the full event envelope and
must parse `event['detail']['findings'][0]` manually — a common source
of KeyError crashes when the event structure changes.

## Finding-to-runbook mapping table (FSBP)

| Control | Finding title | Resource type | Managed runbook |
|---|---|---|---|
| S3.1 | S3 public read access | AwsS3Bucket | `AWS-DisableS3BucketPublicAccess` |
| S3.2 | S3 public write access | AwsS3Bucket | `AWS-DisableS3BucketPublicReadWrite` |
| S3.4 | S3 missing encryption | AwsS3Bucket | `AWS-EnableS3BucketEncryption` |
| S3.6 | S3 missing versioning | AwsS3Bucket | `AWS-EnableS3BucketVersioning` |
| IAM.3 | IAM unused access key | AwsIamUser | `AWS-IAMRevokeUnusedAccessKey` |
| CloudTrail.1 | CloudTrail disabled | AwsCloudTrail | `AWS-EnableCloudTrailLogging` |
| EC2.6 | SG open to 0.0.0.0/0 | AwsEc2SecurityGroup | Custom Lambda required |
| RDS.7 | RDS missing encryption | AwsRdsDbInstance | Custom Lambda required |

## Custom action EventBridge pattern (manual trigger)

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Custom Action"],
  "detail": {
    "actionName": ["triage-to-jira"]
  }
}
```

This fires ONLY when an operator selects findings in the console and
chooses the custom action. It is NOT for automation — use "Imported"
detail-type for automatic remediation.

## Common EventBridge rule failures

| Symptom | Root cause | Fix |
|---|---|---|
| Rule created but Lambda never fires | Wrong `detail-type` (used Custom Action instead of Imported) | Change to "Security Hub Findings - Imported" |
| Lambda fires on all findings, not just CRITICAL | Missing or wrong severity filter in event pattern | Add `detail.findings.Severity.Label` filter |
| Lambda receives full event, KeyError on finding parse | Missing input transformer | Add InputTransformer to the target |
| Lambda fires but SSM execution fails | Wrong resource ID format (ARN vs name) | Strip ARN prefix in the Lambda dispatcher |
| Finding stays in NEW after remediation | Missing `batch-update-findings` call | Add batch-update-findings with RESOLVED status |
| Duplicate remediation on same finding | No dedup check (keying on UpdatedAt) | Key on finding Id, check Workflow.Status before executing |
