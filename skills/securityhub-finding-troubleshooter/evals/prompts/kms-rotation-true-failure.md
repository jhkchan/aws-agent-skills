# Eval prompt: kms-rotation-true-failure

Diagnose the Security Hub finding below. Walk the standard-driven
decision tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, STANDARD, EVIDENCE, SUPPRESSION, REMEDIATION).
The FINDING line must reference the test-case id
`kms-rotation-true-failure`.

Symptom: Security Hub finding
`arn:aws:securityhub:us-east-1:111111111111:finding/pqr012stu` in
account 111111111111 (us-east-1). Control KMS.3, severity MEDIUM,
Compliance.Status=FAILED.

```text
aws securityhub get-findings:
  GeneratorId: "...standards/aws-foundational-security-best-practices/v/1.0.0/KMS.3"
  Resources[0].Id: arn:aws:kms:us-east-1:111111111111:key/billing-prod-key
  Resources[0].Type: AwsKmsKey
  Severity.Label: MEDIUM
  Compliance.Status: FAILED

aws kms describe-keys --key-ids billing-prod-key:
  KeyMetadata:
    KeyId: billing-prod-key
    KeyState: Enabled
    KeyManager: CUSTOMER  (NOT AWS — customer-managed, KMS.3 applies)
    EnableKeyRotation: false  (the failure)
    KeyUsage: ENCRYPT_DECRYPT
    Origin: AWS_KMS
    CreationDate: 2024-01-15  (key is ~18 months old)

aws kms get-key-policy --key-id billing-prod-key:
  Policy allows kms:EnableKeyRotation for the security-admin role
  (operator has the right permission to remediate)

KMS key aliases: alias/billing-prod — used by DynamoDB and S3 Bucket
Keys for the billing workload.

No documented exception in the security team's runbook for skipping
key rotation on billing-prod-key.
```

Emit the standard diagnostic block.
