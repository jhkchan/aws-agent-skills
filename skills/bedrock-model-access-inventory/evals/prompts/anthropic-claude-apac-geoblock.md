# Eval prompt: anthropic-claude-apac-geoblock

Audit the following Bedrock Model Access inventory for security and
compliance posture. Emit the standard VERDICT block (INVENTORY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Bedrock Model Access Inventory:
Region: ap-southeast-1
Account: 111111111111

Enabled models:
  - anthropic.claude-3-5-sonnet-20241022-v2:0 (Anthropic)
  - anthropic.claude-3-haiku-20240307-v1:0 (Anthropic)
  - amazon.nova-pro-v1:0 (Amazon)

Invocation logging configuration:
  s3Config: { bucketName: "bedrock-logs-anthropic-claude-apac-geoblock", keyPrefix: "invocations/" }
  cloudwatchConfig: { logGroupName: "/aws/bedrock/invocations" }
  kinesisConfig: (none)
  textDataDeliveryEnabled: true
  imageDataDeliveryEnabled: true
  embeddingDataDeliveryEnabled: true

KMS encryption:
  customerManagedKey: arn:aws:kms:ap-southeast-1:111111111111:key/anthropic-claude-apac-geoblock

Provisioned throughput: (none)

Guardrails:
  - guardrail-anthropic-claude-apac-geoblock: appliedTo=[anthropic.claude-3-5-sonnet-20241022-v2:0]
