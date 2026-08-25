# Diagnostic Commands — sqs-queue-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Pre-flight safety checks

- **Confirm queue name available:** `aws sqs get-queue-url --queue-name <name> 2>&1 || echo "Name is available"`
- **For FIFO, confirm name ends in `.fifo`** — SQS rejects create without it.
- **Confirm DLQ exists and correct type** — `FifoQueue` attribute must match source.
- **For SSE-KMS, confirm key exists** and policy grants `sqs.<region>.amazonaws.com` permission.
- **Capture existing config for rollback** (if updating): `get-queue-attributes --attribute-names All --output json > /tmp/<queue>-backup-$(date +%s).json`
