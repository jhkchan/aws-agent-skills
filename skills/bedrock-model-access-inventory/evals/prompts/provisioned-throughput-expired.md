# Eval prompt: provisioned-throughput-expired

Audit the following Bedrock Model Access inventory for security and
compliance posture. Emit the standard VERDICT block (INVENTORY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Bedrock Model Access Inventory:
Region: us-east-1
Account: 111111111111

Enabled models:
  - anthropic.claude-3-5-sonnet-20241022-v2:0 (Anthropic)
  - amazon.nova-pro-v1:0 (Amazon)

Invocation logging configuration:
  s3Config: { bucketName: "bedrock-logs-provisioned-throughput-expired", keyPrefix: "invocations/" }
  cloudwatchConfig: { logGroupName: "/aws/bedrock/invocations" }
  kinesisConfig: { streamArn: "arn:aws:firehose:us-east-1:111111111111:deliverystream/bedrock-firehose-provisioned-throughput-expired" }
  textDataDeliveryEnabled: true
  imageDataDeliveryEnabled: true
  embeddingDataDeliveryEnabled: true

KMS encryption:
  customerManagedKey: arn:aws:kms:us-east-1:111111111111:key/provisioned-throughput-expired

Provisioned throughput:
  - pt-provisioned-throughput-expired: model=anthropic.claude-3-5-sonnet-20241022-v2:0, status=expired, commitmentEnd=2026-03-15

Guardrails:
  - guardrail-provisioned-throughput-expired: appliedTo=[anthropic.claude-3-5-sonnet-20241022-v2:0, amazon.nova-pro-v1:0]
