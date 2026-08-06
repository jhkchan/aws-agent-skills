# Eval prompt: encrypted-gp3-attached-ok

Audit the following EBS volume configuration for security and cost
exposure. Emit the standard VERDICT block (RESOURCE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Resource type: volume
Resource id: vol-0fff666encrypted-gp3-ok

Volume configuration (aws ec2 describe-volumes --volume-ids ...):

```json
{
  "VolumeId": "vol-0fff666encrypted-gp3-ok",
  "State": "in-use",
  "Size": 100,
  "VolumeType": "gp3",
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/abc-customer-managed",
  "Iops": 3000,
  "Throughput": 125,
  "Attachments": [
    {
      "InstanceId": "i-0123456789abcdef0",
      "State": "attached",
      "DeleteOnTermination": false,
      "AttachTime": "2026-07-01T08:00:00Z"
    }
  ]
}
```
