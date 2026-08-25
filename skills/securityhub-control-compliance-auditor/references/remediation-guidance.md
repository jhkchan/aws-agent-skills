# Remediation Guidance — Security Hub Control-Compliance Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Control-to-fix-action mapping

For every FAILED or WARNING control, map to the specific remediation action.

### FSBP (Foundational Security Best Practices)

| Control ID | Title | Fix Action | CLI Command |
|---|---|---|---|
| S3.1 | Account-level BPA | Enable all 4 BPA settings | `aws s3control put-public-access-block --account-id <id> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true` |
| S3.2 | Bucket-level BPA | Enable all 4 BPA settings on bucket | `aws s3api put-public-access-block --bucket <name> --public-access-block-configuration BlockPublicAcls=true,...` |
| S3.4 | Bucket versioning | Enable versioning | `aws s3api put-bucket-versioning --bucket <name> --versioning-configuration Status=Enabled` |
| S3.5 | Default encryption | Enable SSE-KMS | `aws s3api put-bucket-encryption --bucket <name> --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"<key-id>"}}]}'` |
| S3.6 | Public read ACL | Remove public ACL + enable BPA | `aws s3api put-bucket-acl --bucket <name> --acl private` + BPA |
| S3.8 | SSL requests only | Deny non-SSL in bucket policy | Deny with `aws:SecureTransport: false` |
| IAM.1 | Admin policy attached | Replace with scoped policy | Scope down via CloudTrail-derived least-privilege |
| IAM.3 | Access Analyzer | Enable IAM Access Analyzer | `aws accessanalyzer create-analyzer --analyzer-name org-analyzer --type ORGANIZATION` |
| IAM.4 | Access key age < 90d | Rotate or deactivate old keys | `aws iam update-access-key --access-key-id <key> --status Inactive` |
| IAM.5 | MFA for IAM users | Enable MFA for all console users | `aws iam create-virtual-mfa-device --virtual-mfa-device-name <name>` |
| IAM.7 | Password policy | Set account password policy | `aws iam update-account-password-policy --minimum-password-length 14 --require-symbols --require-numbers --require-uppercase-characters --require-lowercase-characters --max-password-age 90 --password-reuse-prevention 24` |
| IAM.8 | Unused credentials < 45d | Deactivate unused keys | `aws iam update-access-key --status Inactive` |
| CloudTrail.1 | Trail enabled | Create org-level trail | `aws cloudtrail create-trail --name org-trail --s3-bucket-name <bucket> --is-organization-trail` |
| CloudTrail.2 | Log file validation | Enable validation | `aws cloudtrail update-trail --name <trail> --enable-log-file-validation` |
| CloudTrail.4 | Log encryption (KMS) | Apply KMS CMK to trail | `aws cloudtrail update-trail --name <trail> --kms-key-id <key-arn>` |
| Config.1 | Config enabled all regions | Enable Config recorder | `aws configservice put-configuration-recorder ...` |
| EC2.2 | Default SG restricts traffic | Remove all rules from default SG | `aws ec2 revoke-security-group-ingress --group-id <sg> ...` |
| EC2.4 | EBS snapshot encryption | Enable EBS default encryption | `aws ec2 enable-ebs-encryption-by-default` |
| EC2.6 | VPC flow logs | Enable flow logs for all VPCs | `aws ec2 create-flow-logs --resource-type VPC --resource-ids <vpc-id> --traffic-type ALL --log-group-name <lg>` |
| EC2.15 | SG 0.0.0.0/0 admin port | Restrict SSH/RDP to known CIDR | `aws ec2 revoke-security-group-ingress --group-id <sg> --ip-permissions ...` |
| KMS.1 | KMS key rotation | Enable annual key rotation | `aws kms enable-key-rotation --key-id <key-id>` |
| KMS.2 | KMS key policy not wildcard | Restrict key policy principals | Edit key policy JSON |
| RDS.1 | RDS encryption | Enable encryption at rest | Snapshot → copy with encryption → restore |
| RDS.6 | Enhanced Monitoring | Enable Enhanced Monitoring | `aws rds modify-db-instance --db-instance-identifier <id> --monitoring-interval 60 --monitoring-role-arn <arn>` |
| Lambda.1 | Lambda IAM role check | Ensure dedicated scoped role | `aws lambda update-function-configuration --function-name <name> --role <role-arn>` |
| Lambda.2 | Lambda in VPC | Connect Lambda to VPC | `aws lambda update-function-configuration --vpc-config SubnetIds=...,SecurityGroupIds=...` |

### CIS AWS Foundations Benchmark (v1.2.0 / v1.4.0 / v2.0.0)

| CIS Control | Title | Fix Action |
|---|---|---|
| 1.1 | Avoid root account use | Create IAM admin user; do not use root for daily ops |
| 1.2 | MFA on root | Enable hardware MFA on root (virtual is insufficient for CIS) |
| 1.3 | Credentials unused >90d removed | Deactivate keys; delete inactive users |
| 1.4 | Access keys <90 days | Rotate access keys |
| 1.5 | Password policy | `aws iam update-account-password-policy` (min 14 chars) |
| 1.6 | Hardware MFA for root | Same as CIS 1.2 |
| 1.7 | Password expiry <90d | `--max-password-age 90` |
| 1.8 | Password reuse prevention | `--password-reuse-prevention 24` |
| 1.9 | No password policy | Create one (combines 1.5-1.8) |
| 1.10-1.12 | MFA for all IAM users | Enable MFA for every console user |
| 1.13-1.16 | No excessive access keys | Max 1 key per user; rotate inactive |
| 1.20 | IAM Access Analyzer | Enable (maps to FSBP IAM.3) |
| 1.21 | IAM credential report | `aws iam get-credential-report` monthly |
| 2.1 | CloudTrail enabled | Multi-region trail (maps to FSBP CloudTrail.1) |
| 2.2 | Log validation | Enable (maps to FSBP CloudTrail.2) |
| 2.3 | S3 bucket access logging | Enable server access logging on CloudTrail bucket |
| 2.4 | CloudTrail to CW Logs | `aws cloudtrail update-trail` + subscription filter |
| 2.5 | Config enabled | Maps to FSBP Config.1 |
| 2.6 | S3 bucket MFA delete | `aws s3api put-bucket-versioning --file mfa.json` (requires root) |
| 2.7-2.9 | CloudTrail logs encrypted | KMS encryption on trail |
| 3.1-3.4 | Security Hub alerts on root/MFA/unauthorized | CW metric filter + alarm + SNS |
| 3.5-3.14 | Network security / SG | Restrict 0.0.0.0/0 (maps to FSBP EC2.15) |
| 4.1 | No SG 0.0.0.0/0 on port 22 | Restrict SSH |
| 4.2 | No SG 0.0.0.0/0 on port 3389 | Restrict RDP |

### PCI-DSS v3.2.1 and NIST SP 800-53 Rev. 5

PCI controls (`PCI.EC2.1`, `PCI.IAM.1`, `PCI.S3.1`) and NIST controls
(`NIST.800-53.r5.*`) share the same underlying Config rules as FSBP. Map by
resource type + issue, not by the control ID prefix. The fix actions are
identical.

**Cross-standard deduplication:** The same resource may have 3-4 findings for
the same underlying issue. The fix is the same — apply once, all findings
re-evaluate independently.

## Remediation guidance

### For FAILED findings

1. Identify the control ID and look up the fix action in the mapping table.
2. Run the pre-flight safety checks (confirm resource exists, capture state,
   dry-run if batch).
3. Apply the fix via the CLI command in the mapping table.
4. Update the finding workflow status to RESOLVED:
   `aws securityhub batch-update-findings --finding-identifiers
   Id=<id>,ProductArn=<arn> --workflow Status=RESOLVED --note "Applied
   <fix-action>, awaiting re-evaluation."`
5. Wait for the next evaluation cycle (12-24h for periodic, 5-30 min for
   config-change). If the finding auto-updates to `PASSED`, remediation is
   confirmed. If still `FAILED` after 48h, re-investigate the resource.
6. For cross-standard duplicates, apply the fix once — all findings
   re-evaluate independently.

### For WARNING findings

- **Suppressed FAILED:** Review the suppression justification. If the
  compensating control is still valid, document it in a compliance exception
  register. If stale (no note, > 90 days), unsuppress:
  `aws securityhub batch-update-findings --workflow Status NEW`. If the
  control now passes, auto-close; if still failing, proceed to the FAILED
  remediation path.
- **Resolved-pending:** If > 48h since resolution and still FAILED,
  re-investigate the resource. If < 48h, wait for the next cycle.
- **NOT_AVAILABLE (Config gap):** Enable AWS Config in the affected region.

### For NOT_APPLICABLE findings

- **NO_RESOURCES / DISABLED_CONTROL:** No action. Document that the control
  does not apply to this account's resource profile.
- **Integration findings:** Route to the appropriate detector skill.

