# Eval prompt: single-destination-logging

Audit the following Bedrock Model Access inventory for security and
compliance posture. Emit the standard VERDICT block (INVENTORY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Bedrock Model Access Inventory:
Region: us-east-1
Account: 111111111111

Enabled models:
  - amazon.nova-pro-v1:0 (Amazon)
  - amazon.titan-text-express-v1 (Amazon)

Invocation logging configuration:
  s3Config: { bucketName: "bedrock-logs-single-destination-logging", keyPrefix: "invocations/" }
  cloudwatchConfig: (none)
  kinesisConfig: (none)
  textDataDeliveryEnabled: true
  imageDataDeliveryEnabled: false
  embeddingDataDeliveryEnabled: false

KMS encryption:
  customerManagedKey: arn:aws:kms:us-east-1:111111111111:key/single-destination-logging

Provisioned throughput: (none)

Guardrails: (none)
