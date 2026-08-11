# Managed Rules and Compliance Frameworks Reference

Supplementary reference for the Config Rule Compliance Automator skill.
Use when selecting managed rules for a compliance framework, mapping CIS
controls to Config rules, or deciding between managed, custom policy,
and custom Lambda rules.

## Managed rule selection by framework

### CIS AWS Foundations Benchmark v1.x (IAM)

| CIS Control | Managed Rule ID | Coverage | Custom Needed? |
|---|---|---|---|
| 1.1 Avoid root access keys | `IAM_ROOT_ACCESS_KEY_CHECK` | Full | No |
| 1.2 MFA on root account | `ROOT_ACCOUNT_MFA_ENABLED` | Full | No |
| 1.3 Root credentials unused | `IAM_ROOT_ACCESS_KEY_CHECK` | Full | No |
| 1.4 IAM password policy | `IAM_PASSWORD_POLICY` | Full | No |
| 1.5 MFA enabled for all IAM users | `IAM_USER_MFA_ENABLED_CHECK` | Partial (needs custom for "all") | Yes for strict |
| 1.6 Hardware MFA for root | Custom needed | **Gap** | Yes |
| 1.7 Password expiration | `IAM_PASSWORD_POLICY` | Partial | Yes for strict |
| 1.8-1.12 Various IAM checks | Multiple managed rules | Full | No |
| 1.13 CloudTrail enabled | `CLOUDTRAIL_ENABLED` | Full | No |
| 1.14 S3 bucket access logging | `S3_BUCKET_LOGGING_ENABLED` | Full | No |
| 1.15 S3 bucket MFA delete | Custom needed | **Gap** | Yes |
| 1.16-1.17 S3 bucket public access | `S3_BUCKET_PUBLIC_READ_PROHIBITED` | Full | No |
| 1.18 IAM XaaS credential report | `IAM_USER_GROUP_MEMBERSHIP_CHECK` | Partial | No |
| 1.19-1.20 SSL on buckets | `S3_BUCKET_SSL_REQUESTS_ONLY` | Full | No |
| 1.21 IAM user unused | `IAM_USER_UNUSED_CREDENTIALS_CHECK` | Full | No |
| 1.22 IAM access key rotation | `IAM_ACCESS_KEY_ROTATED` | Full | No |

### CIS AWS Foundations Benchmark v2.x (Networking)

| CIS Control | Managed Rule ID | Coverage | Custom Needed? |
|---|---|---|---|
| 2.1 Default SG restrict traffic | Custom needed | **Gap** | Yes (Lambda) |
| 2.2 SG open only to authorized ports | `VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS` | Full | No |
| 2.3 SG not open to 0.0.0.0/0 | `VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS` | Full | No |
| 2.4 Default VPC | Custom needed | **Gap** | Yes |
| 2.5-2.9 Flow logs, peering | `VPC_FLOW_LOGS_ENABLED` | Partial | No |

### CIS AWS Foundations Benchmark v3.x (Logging)

| CIS Control | Managed Rule ID | Coverage | Custom Needed? |
|---|---|---|---|
| 3.1 CloudTrail enabled | `CLOUDTRAIL_ENABLED` | Full | No |
| 3.2 CloudTrail multi-region | `MULTI_REGION_CLOUDTRAIL_ENABLED` | Full | No |
| 3.3 KMS CMK for CloudTrail | Custom needed | **Gap** | Yes |
| 3.4 CloudTrail log file validation | `CLOUDTRAIL_ENABLED` | Partial | No |
| 3.5-3.14 Various logging configs | `S3_BUCKET_LOGGING_ENABLED`, `CLOUDWATCH_ALARMS_ENABLED` | Partial | No |

### PCI-DSS 3.2.1

| PCI Control | Managed Rule ID | Coverage |
|---|---|---|
| Requirement 3 (Protect stored data) | `S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED` | Full |
| Requirement 7 (Restrict access) | `IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS` | Full |
| Requirement 8 (Identify users) | `IAM_USER_MFA_ENABLED_CHECK` | Full |
| Requirement 10 (Track/monitor) | `CLOUDTRAIL_ENABLED`, `MULTI_REGION_CLOUDTRAIL_ENABLED` | Full |
| Requirement 11 (Security testing) | `VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS` | Full |

### NIST 800-53 Rev 5

| NIST Control Family | Managed Rule IDs | Coverage |
|---|---|---|
| AC (Access Control) | `IAM_PASSWORD_POLICY`, `IAM_USER_MFA_ENABLED_CHECK` | ~70% |
| AU (Audit) | `CLOUDTRAIL_ENABLED`, `S3_BUCKET_LOGGING_ENABLED` | ~85% |
| CM (Configuration) | `AWS_CONFIG_ENABLED` | ~60% |
| IA (Identification) | `ROOT_ACCOUNT_MFA_ENABLED`, `IAM_ACCESS_KEY_ROTATED` | ~75% |
| SC (System Protection) | `ACM_CERTIFICATE_EXPIRATION_CHECK`, `VPC_FLOW_LOGS_ENABLED` | ~65% |

## Custom rule types and when to use each

| Rule Type | Cost | Maintenance | Use When |
|---|---|---|---|
| AWS Managed | Free | Zero | A managed rule exists for the check |
| Custom Policy (Guard 2) | Free (server-side) | Low (policy text) | Logic expressible as policy, no external lookups |
| Custom Lambda | Lambda charges | High (runtime, deps) | Multi-resource correlation, external data, complex logic |

## Conformance pack deployment matrix

| Deployment Method | Multi-Account | Multi-Region | Auto-Deploy New Accounts | IAM Capabilities Required |
|---|---|---|---|---|
| `put-conformance-pack` (single account) | No | Per-call | No | No |
| StackSet (SELF_MANAGED) | Yes (per-role) | Yes | No | Yes |
| StackSet (SERVICE_MANAGED) | Yes (OU-wide) | Yes | Yes | Yes |
| Organizational Config Rule | Yes (org-wide) | Per-region call | Yes | No (uses SLR) |

## SSM remediation runbook selection

| Finding Type | Managed Runbook | Trigger |
|---|---|---|
| S3 public access | `AWS-DisableS3BucketPublicAccess` | Automatic |
| S3 missing encryption | `AWS-EnableS3BucketEncryption` | Automatic |
| S3 missing versioning | `AWS-EnableS3BucketVersioning` | Automatic |
| IAM unused access key | `AWS-IAMRevokeUnusedAccessKey` | Automatic |
| CloudTrail logging disabled | `AWS-EnableCloudTrailLogging` | Automatic |
| Security group open to 0.0.0.0/0 | Custom needed | Manual |
| Default SG with ingress | Custom needed | Manual |

## Config Aggregator query patterns

```bash
# All NON_COMPLIANT rules across all accounts
aws configservice describe-aggregate-compliance-by-config-rules \
  --configuration-aggregator-name org-aggregator \
  --filters '{"ComplianceType": "NON_COMPLIANT"}'

# Specific rule compliance per account
aws configservice describe-aggregate-compliance-by-config-rules \
  --configuration-aggregator-name org-aggregator \
  --filters '{"ConfigRuleName": "s3-bucket-server-side-encryption-enabled"}'

# Compliance summary across organization
aws configservice describe-aggregate-compliance-by-conformance-packs \
  --configuration-aggregator-name org-aggregator
```

## MaximumExecutionFrequency guidance

| Rule Type | Recommended Frequency | Rationale |
|---|---|---|
| Security-critical (root MFA, trail) | `One_Hour` | Fast detection of security regressions |
| Compliance (encryption, versioning) | `Six_Hours` | Balance between detection speed and cost |
| Operational (tagging) | `TwentyFour_Hours` | Low urgency; cost minimization |
