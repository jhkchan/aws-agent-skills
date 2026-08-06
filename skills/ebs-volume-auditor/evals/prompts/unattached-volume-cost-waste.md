# Eval prompt: unattached-volume-cost-waste

Audit the following EBS volume configuration for security and cost
exposure. Emit the standard VERDICT block (RESOURCE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Resource type: volume
Resource id: vol-0ccc333unattached-volume

Volume configuration (aws ec2 describe-volumes --volume-ids ...):

```json
{
  "VolumeId": "vol-0ccc333unattached-volume",
  "State": "available",
  "Size": 500,
  "VolumeType": "gp3",
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/abc-customer-managed",
  "CreateTime": "2026-03-01T08:00:00Z",
  "Attachments": []
}
```

Resource tags:
- Key: `lastAttached`, Value: `2026-03-15`

Today: 2026-08-02
