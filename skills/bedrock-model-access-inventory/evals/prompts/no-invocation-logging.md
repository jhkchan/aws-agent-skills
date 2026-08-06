# Eval prompt: no-invocation-logging

Audit the following Bedrock Model Access inventory for security and
compliance posture. Emit the standard VERDICT block (INVENTORY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Bedrock Model Access Inventory:
Region: us-east-1
Account: 111111111111

Enabled models:
  - anthropic.claude-3-5-sonnet-20241022-v2:0 (Anthropic)
  - amazon.nova-pro-v1:0 (Amazon)
  - amazon.titan-text-express-v1 (Amazon)

Invocation logging configuration:
  s3Config: (none)
  cloudwatchConfig: (none)
  kinesisConfig: (none)
  textDataDeliveryEnabled: false
  imageDataDeliveryEnabled: false
  embeddingDataDeliveryEnabled: false

KMS encryption:
  customerManagedKey: (none — AWS-managed)

Provisioned throughput: (none)

Guardrails: (none)
