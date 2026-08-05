# Eval prompt: no-kms-customer-key

Audit the following Bedrock Model Access inventory for security and
compliance posture. Emit the standard VERDICT block (INVENTORY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Bedrock Model Access Inventory:
Region: us-east-1
Account: 111111111111

Enabled models:
  - amazon.nova-pro-v1:0 (Amazon)
  - amazon.nova-lite-v1:0 (Amazon)
  - amazon.titan-text-express-v1 (Amazon)

Invocation logging configuration:
  s3Config: { bucketName: "bedrock-logs-no-kms-customer-key", keyPrefix: "invocations/" }
  cloudwatchConfig: { logGroupName: "/aws/bedrock/invocations" }
  kinesisConfig: (none)
  textDataDeliveryEnabled: true
  imageDataDeliveryEnabled: true
  embeddingDataDeliveryEnabled: false

KMS encryption:
  customerManagedKey: (none — AWS-managed)

Provisioned throughput: (none)

Guardrails: (none)
