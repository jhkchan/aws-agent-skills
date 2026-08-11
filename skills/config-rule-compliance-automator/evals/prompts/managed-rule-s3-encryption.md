# Eval prompt: managed-rule-s3-encryption

Design a Config rule compliance automation for S3 encryption. Emit the
standard COMPLIANCE block (RULES, REMEDIATION, AGGREGATOR,
FRAMEWORK_DEPLOYMENT, VERDICT, TEMPLATE).

Design reference: managed-rule-s3-encryption
Account: 111111111111
Region: us-east-1 (multi-region required)

Config recorder: active, allSupported=true.
Framework: CIS AWS Foundations Benchmark (control 2.1 — S3 encryption).
Target rule: s3-bucket-server-side-encryption-enabled (AWS-managed).
Remediation: AWS-EnableS3BucketEncryption (automatic, reversible).
Deployment: StackSet with auto-deployment, all active regions.
Config Aggregator: configured, org-wide.
