# Eval prompt: organizational-config-rule

Design an organizational config rule deployment for org-wide S3
encryption compliance. Emit the standard COMPLIANCE block (RULES,
REMEDIATION, AGGREGATOR, FRAMEWORK_DEPLOYMENT, VERDICT, TEMPLATE).

Design reference: organizational-config-rule
Organization management account: 111111111111
Member accounts: all (auto-propagated)

Rule: S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED (managed, org-level).
Remediation: AWS-EnableS3BucketEncryption (automatic).
Organizations integration: enabled.
AWSServiceRoleForConfig: present in management account.
Config recorder: active in all member accounts.

Include the put-organization-config-rule deployment CLI.
