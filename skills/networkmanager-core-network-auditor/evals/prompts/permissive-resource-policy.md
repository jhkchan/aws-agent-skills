# Eval prompt: permissive-resource-policy

Audit the following Network Manager core network configuration for security
and operational exposure. Emit the standard VERDICT block (CORE_NETWORK,
VERDICT, REASON, FINDINGS, REMEDIATION).

Core network id: core-network-def456
Core network ARN: arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-def456
OwnerAccountId: 111111111111
State: AVAILABLE
Policy generation (LATEST): 3
Policy generation (LIVE): 3

Attachments:

  - AttachmentId: attachment-bbb222
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:111111111111:vpc/vpc-bbb222
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-east-1
    Segment: prod
    Cidrs: [10.1.0.0/24]

Resource policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "networkmanager:*",
      "Resource": "arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-def456"
    }
  ]
}
```

Core network policy (segment-actions):

  - segment: prod
    share-with: [prod]
