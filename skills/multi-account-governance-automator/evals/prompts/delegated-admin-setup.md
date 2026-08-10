# Eval prompt: delegated-admin-setup

Design the delegated administration layer for our org. Emit the standard
GOVERNANCE block.

Requirements:
- Org: 40 member accounts, all-features
- Audit account: 111111111111
- Log-archive account: 222222222222
- Delegate to audit account:
  - GuardDuty (enable-organization-admin-account)
  - Security Hub (CIS + AWS Foundational standards)
  - Config aggregator (OrganizationAggregationSource, AllRegions=true)
  - Access Analyzer
- CloudTrail org trail delivering to log-archive S3 bucket
  org-trail-logs-2222 with KMS encryption
- Log-archive S3 bucket policy uses aws:PrincipalOrgID condition (not
  enumerated account IDs) for s3:PutObject from cloudtrail.amazonaws.com
- KMS key policy allows member accounts kms:GenerateDataKey for
  CloudTrail via aws:PrincipalOrgID
- IAM Identity Center: AWSAdministratorAccess (1h) +
  AWSReadOnlyAccess (4h) + EmergencyAdmin (break-glass, sealed envelope,
  tested 2026-07-15)
- Resource Explorer aggregator index in audit account, view
  CrossAccountView, local indexes in each member account
- One org trail covers all members + all regions (no per-account trails)

Expected: AUTOMATED. The delegation layer centralizes all security and
logging services in the audit account, the CloudTrail org trail delivers
to log-archive with org-scoped bucket and KMS policies, Identity Center
includes a tested break-glass path, and Resource Explorer provides
cross-account search.
