# Eval prompt: unencrypted-volume-compliance-violation

Audit the following EBS volume configuration for security and cost
exposure. Emit the standard VERDICT block (RESOURCE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Resource type: volume
Resource id: vol-0bbb222unencrypted-volume

Volume configuration (aws ec2 describe-volumes --volume-ids ...):

```json
{
  "VolumeId": "vol-0bbb222unencrypted-volume",
  "State": "in-use",
  "Size": 100,
  "VolumeType": "gp2",
  "Encrypted": false,
  "Attachments": [
    {
      "InstanceId": "i-0123456789abcdef0",
      "State": "attached",
      "DeleteOnTermination": false,
      "AttachTime": "2026-05-01T08:00:00Z"
    }
  ]
}
```

Region encryption-by-default: true
