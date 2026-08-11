# Eval prompt: cost-analysis-bulk-transfer-ready

Plan the following 50 TB data migration with cost analysis (Transfer
Acceleration vs Direct Connect) and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, COST,
NOTES).

Operation: compare-direct-connect
BucketName: migration-target
Region: us-east-1

```json
{
  "AccelerateConfiguration": {"Status": "Enabled"},
  "TransferDetails": {
    "Source": "Tokyo data center (ap-northeast-1)",
    "Destination": "migration-target bucket (us-east-1)",
    "Volume": "50 TB",
    "AccelerationRate": 0.025
  },
  "DirectConnect": {
    "PortSpeed": "1 Gbps",
    "PortHourlyRate": 0.30,
    "DataTransferOutRate": 0.0204,
    "EstimatedTransferTime": "5.7 days at 80% utilization"
  }
}
```
