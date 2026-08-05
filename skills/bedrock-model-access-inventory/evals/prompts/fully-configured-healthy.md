# Eval prompt: fully-configured-healthy

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
  s3Config: { bucketName: "bedrock-logs-fully-configured-healthy", keyPrefix: "invocations/" }
  cloudwatchConfig: { logGroupName: "/aws/bedrock/invocations" }
  kinesisConfig: { streamArn: "arn:aws:firehose:us-east-1:111111111111:deliverystream/bedrock-firehose-fully-configured-healthy" }
  textDataDeliveryEnabled: true
  imageDataDeliveryEnabled: true
  embeddingDataDeliveryEnabled: true

KMS encryption:
  customerManagedKey: arn:aws:kms:us-east-1:111111111111:key/fully-configured-healthy

Provisioned throughput:
  - pt-fully-configured-healthy: model=amazon.nova-pro-v1:0, status=active, commitmentEnd=2026-12-31

Guardrails:
  - guardrail-fully-configured-healthy: appliedTo=[amazon.nova-pro-v1:0, amazon.nova-lite-v1:0, amazon.titan-text-express-v1]
