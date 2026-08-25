# Security Hub Control Catalogue and Remediation

Supplementary reference for the Security Hub Finding Troubleshooter
skill. Loaded on-demand when an investigation needs the full control
catalogue, severity mapping, or ready-to-use Automation Rule criteria
JSON.

## Standards overview

| Standard | ARN suffix | Typical control count | Notes |
|---|---|---|---|
| CIS AWS Foundations Benchmark 1.4 | `cis-aws-foundations-benchmark/v/1.4.0` | ~36 | Stable IDs `CIS.1.x`–`CIS.5.x`. v1.4 added Detective and Macie controls. |
| CIS AWS Foundations Benchmark 3.0 | `cis-aws-foundations-benchmark/v/3.0.0` | ~25 | Re-structured to NIST CSF mapping. Verify `GeneratorId` before applying v1.x runbooks. |
| PCI DSS 3.2.1 | `pci-dss/v/3.2.1` | ~25 | Required for PCI-DSS compliance attestation. |
| AWS Foundational Security Best Practices (FSBP) | `aws-foundational-security-best-practices/v/1.0.0` | ~250+ | Service-prefixed control IDs `S3.1`, `EC2.8`, `KMS.3`. Most rapidly updated. |
| NIST 800-53 Rev. 5 | `nist-800-53/v/5.0.0` | ~200+ | Maps to NIST control families (AC, AU, SC, etc.). |

## Severity mapping

Security Hub assigns `Severity.Label` from the standard's scoring. The
mapping is NOT 1:1 with Config rule severity.

| Security Hub Severity | CIS | PCI | FSBP | Typical action |
|---|---|---|---|---|
| `CRITICAL` | n/a (CIS uses numeric) | n/a (PCI uses numeric) | 90+ score | Page on-call; auto-remediate |
| `HIGH` | ≥ 7.0 numeric | ≥ 6.0 | 70-89 score | Triage within 24h |
| `MEDIUM` | 4.0-6.9 | 3.0-5.9 | 40-69 score | Triage within 72h |
| `LOW` | 1.0-3.9 | 1.0-2.9 | 1-39 score | Backlog grooming |
| `INFORMATIONAL` | < 1.0 | < 1.0 | n/a | Logging only |

## Per-service control catalogue

### S3 controls (FSBP S3.1–S3.10)

| Control | Tests | Probe | Remediation |
|---|---|---|---|
| `S3.1` | Account-level BPA enabled | `aws s3control get-public-access-block` | `put-public-access-block` with all 4 flags true |
| `S3.2` | Bucket-level public ACL prohibition | `aws s3api get-bucket-acl` | `put-bucket-acl --acl private` |
| `S3.3` | Bucket-level public policy prohibition | `aws s3api get-bucket-policy` | Remove public `Principal: "*"` grant |
| `S3.4` | Bucket-default SSE enabled | `aws s3api get-bucket-encryption` | `put-bucket-encryption` with AES256 or aws:kms |
| `S3.5` | DI restrictive (subscriber-only) | n/a | Specialized — see Security Hub docs |
| `S3.6` | Bucket KMS-enabled SSE | `aws s3api get-bucket-encryption` | `put-bucket-encryption` with aws:kms |
| `S3.8` | Bucket SSL-only | `aws s3api get-bucket-policy` (aws:SecureTransport) | Add `aws:SecureTransport: false` deny |
| `S3.9` | Versioning enabled | `aws s3api get-bucket-versioning` | `put-bucket-versioning --versioning-configuration Status=Enabled` |
| `S3.10` | MFA delete enabled | `aws s3api get-bucket-versioning` (MfaDelete) | `put-bucket-versioning --mfa` (root only) |

### IAM controls (CIS.1.x / FSBP.IAM.x)

| Control | Tests | Probe | Remediation |
|---|---|---|---|
| `CIS.1.3` | Access keys ≤ 90 days old | `aws iam get-credential-report` | Rotate via `create-access-key` + `delete-access-key` |
| `CIS.1.4` | Root MFA enabled | `aws iam get-account-summary.AccountMFAEnabled` | `create-virtual-mfa-device` (root only) |
| `CIS.1.5–1.11` | Password policy fields | `aws iam get-account-password-policy` | `update-account-password-policy` |
| `CIS.1.12` | Root API key absence | `aws iam get-credential-report` (root row) | Delete root access keys |
| `CIS.1.20` | No support role outside lambda | `aws iam list-roles` | Convert inline AWSSupportServiceRolePolicy |
| `FSBP.IAM.6` | Hardware MFA for root | `aws iam list-virtual-mfa-devices` | Hardware MFA via `create-mfa-device` |
| `FSBP.IAM.7` | MFA for all IAM users | credential report + `list-virtual-mfa-devices` | Enroll users in MFA |

### EC2 controls (FSBP.EC2.x)

| Control | Tests | Probe | Remediation |
|---|---|---|---|
| `EC2.1` | No public EIP on EC2 | `aws ec2 describe-addresses` | Re-assign to NAT Gateway |
| `EC2.2` | No SG 0.0.0.0/0 on SSH | `aws ec2 describe-security-groups` | `revoke-security-group-ingress` + scoped rule |
| `EC2.4` | No SG 0.0.0.0/0 on RDP | Same | Same |
| `EC2.6` | VPC flow logs enabled | `aws ec2 describe-flow-logs` | `create-flow-logs` |
| `EC2.8` | IMDSv2 required | `aws ec2 describe-instances.MetadataOptions` | `modify-instance-metadata-options --http-tokens required` |
| `EC2.16` | No unencrypted EBS volumes | `aws ec2 describe-volumes` | `create-snapshot`, copy encrypted, swap volume |
| `EC2.18` | Security group description present | `aws ec2 describe-security-groups` | Update description |

### KMS controls

| Control | Tests | Probe | Remediation |
|---|---|---|---|
| `KMS.3` | CMK rotation enabled | `aws kms describe-keys.EnableKeyRotation` | `enable-key-rotation --key-id <key-id>` |
| `KMS.4` | Key policy not wildcard | `aws kms get-key-policy` | Tighten `Principal` |

### CloudTrail / Config controls

| Control | Tests | Probe | Remediation |
|---|---|---|---|
| `CloudTrail.1` | Trail enabled | `aws cloudtrail describe-trails` | `create-trail` |
| `CloudTrail.2` | Multi-region trail | Same (`IsMultiRegionTrail`) | `update-trail --is-multi-region-trail` |
| `CloudTrail.4` | S3 data events | `aws cloudtrail get-event-selectors` | `put-event-selectors` with `DataResources: s3:::` |
| `CloudTrail.7` | Log file validation | `describe-trails.LogFileValidationEnabled` | `update-trail --enable-log-file-validation` |
| `Config.1` | Recorder ON | `aws configservice describe-configuration-recorders` | `start-configuration-recorder` |

## Automation Rule criteria JSON

The `create-automation-rule` CLI takes a `--criteria` JSON object. Each
field accepts `EQUALS` / `PREFIX` / `NOT_EQUALS` etc.

### CI deployment role keys (CIS.1.3) — archive

```json
{
  "Criteria": {
    "GeneratorId": [{ "Value": "CIS.1.3", "Comparison": "PREFIX" }],
    "Resources.AwsIamAccessKey.PrincipalName": [{
      "Value": "ci-deployment-role-prod",
      "Comparison": "EQUALS"
    }]
  }
}
```

Action: `{Type: FINDING_FIELDS_UPDATE, FindingFieldsUpdate: {Workflow: {Status: SUPPRESSED}}}`

### Documented public S3 bucket (S3.2) — lower severity

```json
{
  "Criteria": {
    "GeneratorId": [{ "Value": "S3.2", "Comparison": "PREFIX" }],
    "Resources.Id": [{
      "Value": "arn:aws:s3:::public-website-assets-prod",
      "Comparison": "EQUALS"
    }]
  }
}
```

Action: `{Type: FINDING_FIELDS_UPDATE, FindingFieldsUpdate: {Severity: {Label: INFORMATIONAL}}}`

### Sandbox account (EC2.8 IMDSv2) — archive

```json
{
  "Criteria": {
    "GeneratorId": [{ "Value": "EC2.8", "Comparison": "PREFIX" }],
    "AwsAccountId": [{ "Value": "111111111111", "Comparison": "EQUALS" }]
  }
}
```

Action: `{Type: FINDING_FIELDS_UPDATE, FindingFieldsUpdate: {Workflow: {Status: SUPPRESSED}}}`

## NOT_AVAILABLE StatusReason codes

| Code | Meaning | Action |
|---|---|---|
| `CONFIG_NO_EVALUATIONS` | Config rule has not run yet | Wait 5-30 min for first eval cycle. |
| `CONFIG_RULE_NOT_APPLICABLE` | Resource type not in scope (e.g., Lambda control, no Lambda) | Suppress via Automation Rule or accept as permanent NOT_AVAILABLE. |
| `CONFIG_EVALUATION_ERROR` | Config rule Lambda errored | Inspect CloudWatch Logs; fix the Lambda. |
| `INSUFFICIENT_DATA` | Config has no data for the resource | Verify recorder covers the resource type and region. |
| `RESOURCE_MISSING` | Resource was deleted between detection and eval | Re-evaluation will clear after 3-5 days. |

## Cross-account aggregation topology

```
[Administrator Account]                  [Member Account 1]
  aws securityhub enable-organization-admin  ↓
       ↓                                   aws securityhub get-administrator-account
  aws securityhub create-members ----------> (invitation)
       ↓                                   aws securityhub accept-administrator-invitation
  aws securityhub get-finding-aggregator   ↓
       ↓ (up to 5 min latency)             findings flow UP to aggregator
  get-findings (aggregated view)
```

Common failure modes:

- Member not in `list-members` → re-invite via `create-members`.
- Member's `administrator-account` doesn't match aggregator → member
  was re-invited by a different administration account (org reshuffle).
- Aggregator's `Regions` list excludes the member's region → findings
  in unsupported regions never aggregate.

## Step 13 — Suppression CLI and FP-class patterns

```bash
aws securityhub create-automation-rule \
  --rule-name "archive-cis-1-3-known-ci-keys" --rule-order 1 \
  --description "Archive CIS.1.3 findings on the CI deployment role" \
  --criteria '<json-criteria>' \
  --actions '[{"Type":"FINDING_FIELDS_UPDATE","FindingFieldsUpdate":{"Workflow":{"Status":"SUPPRESSED"}}}]'
```

**Suppression patterns by FP class** (full criteria JSON in
`references/control-catalogue-and-remediation.md`):

- **CI deployment role keys (CIS.1.3)** — filter on
  `Resources[0].Details.AwsIamAccessKey.PrincipalName` containing
  `<ci-role-name>` AND GeneratorId containing `CIS.1.3`.
- **Documented public S3 bucket (S3.2)** — filter on
  `Resources[0].Id` containing `<bucket-arn>` AND GeneratorId
  containing `S3.2`.
- **Test instance in sandbox account (EC2.8)** — filter on
  `AwsAccountId=<sandbox>` AND `Resources[0].Type=AwsEc2Instance`.

