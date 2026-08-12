# Eval: compliance-remediation-association

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — tag targets, GatherSoftwareInventory document, EventBridge rule on NON_COMPLIANT triggering StartAssociationsOnce, idempotency prerequisite

## Prompt

Create an SSM State Manager association named
InventoryProduction in us-east-1. Use document
AWS-GatherSoftwareInventory. Target instances tagged
Environment=production. Schedule rate(30 minutes). Apply at
creation. Integer rate control: max-concurrency=50,
max-errors=5. Output to s3://my-ssm-output/ssm-output/ (SSE-KMS).
Wire this association for auto-remediation when the compliance
state flips to NON_COMPLIANT — EventBridge rule triggering
StartAssociationsOnce. Confirm AWS-GatherSoftwareInventory is
idempotent.
