# Error Handling — sqs-queue-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Error-handling branches

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameterValueException: FIFO queue name must end with .fifo` | FIFO created without `.fifo` suffix | Rename with `.fifo` suffix |
| `InvalidParameterValueException: Dead-letter queue does not exist` | Redrive policy references non-existent DLQ | Create DLQ first, then set redrive |
| `KMSAccessDeniedException` | Role lacks `kms:Decrypt` on SSE-KMS key | Add `kms:Decrypt` + `kms:GenerateDataKey*` |
| `QueueDeletedRecently: Must wait 60 seconds` | Queue deleted within last 60s | Wait 60 seconds, then recreate |
| Messages stuck, not moving to DLQ | maxReceiveCount too high, or consumer deleting/re-receiving | Check `ApproximateNumberOfMessagesReceived` vs `Deleted` |
| Duplicate processing despite FIFO | VisibilityTimeout too short | Increase to >= p99 processing time |
| FIFO throughput throttle (429) | Exceeding 300 TPS (standard) or 1500 TPS (HT) | Enable high-throughput FIFO or use more message groups |
