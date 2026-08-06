# Eval prompt: well-segmented-core-network

Audit the following Network Manager core network configuration for security
and operational exposure. Emit the standard VERDICT block (CORE_NETWORK,
VERDICT, REASON, FINDINGS, REMEDIATION).

Core network id: core-network-mno345
Core network ARN: arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-mno345
OwnerAccountId: 111111111111
State: AVAILABLE
Policy generation (LATEST): 7
Policy generation (LIVE): 7

Attachments:

  - AttachmentId: attachment-fff666
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:111111111111:vpc/vpc-fff666
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-east-1
    Segment: prod
    Cidrs: [10.10.0.0/24]
  - AttachmentId: attachment-ggg777
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:111111111111:vpc/vpc-ggg777
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-east-1
    Segment: non-prod
    Cidrs: [10.20.0.0/24]

Resource policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "networkmanager:*",
      "Resource": "arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-mno345"
    }
  ]
}
```

Core network policy (segment-actions):

  - segment: prod
    share-with: [prod]
  - segment: non-prod
    share-with: [non-prod]
