# Advanced Patterns — Backup Audit Automator

## Mindset — the three misconceptions
Three misconceptions dominate backup audit automation at provisioning
time:

- **"Backup plans equal backup compliance."** They do NOT. Having a
  backup plan does not mean ALL resources are covered. A backup audit
  identifies resources that are NOT in any backup plan — these are the
  compliance gaps. The compliance report template
  (COMPLIANCE_REPORT) explicitly lists resources without backup
  coverage.

- **"Vault Lock governance mode is the same as compliance mode."** It
  is NOT. Compliance mode is IMMUTABLE — once a Vault Lock is set in
  compliance mode, NO user (including root) can delete the vault or
  change the lock. Governance mode allows privileged users to bypass
  the lock. For regulatory compliance (SEC, FINRA, HIPAA), compliance
  mode is required. Governance mode is for operational guardrails, not
  regulatory immutability.

- **"Encryption on recovery points is automatic."** It is NOT
  guaranteed. While AWS Backup can encrypt recovery points with KMS,
  the KMS key must be explicitly configured in the backup plan. If the
  plan does not specify a KMS key, recovery points may use the default
  AWS-managed key or no encryption (depending on the resource type).
  An encryption audit verifies that ALL recovery points have KMS
  encryption.

## Cross-dependency gotchas
**Cross-dependency gotchas:**
- Report plans deliver to S3. The S3 bucket policy MUST allow
  `backup.amazonaws.com` to write to the bucket. Without the policy,
  reports are not delivered.
- Compliance reports list resources NOT covered by backup plans. This
  is different from backup job reports (which list backup job status).
- Vault Lock in compliance mode CANNOT be reversed. Once set, it is
  permanent. Governance mode CAN be reversed by privileged users.
- SNS alerting requires the SNS topic policy to allow the CloudWatch
  alarm or EventBridge rule to publish.
