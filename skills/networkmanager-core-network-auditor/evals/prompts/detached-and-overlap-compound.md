# Eval prompt: detached-and-overlap-compound

Audit the following Network Manager core network configuration for security
and operational exposure. Emit the standard VERDICT block (CORE_NETWORK,
VERDICT, REASON, FINDINGS, REMEDIATION).

Core network id: core-network-pqr678
Core network ARN: arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-pqr678
OwnerAccountId: 111111111111
State: AVAILABLE
Policy generation (LATEST): 3
Policy generation (LIVE): 3

Attachments:

  - AttachmentId: attachment-hhh888
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:111111111111:vpc/vpc-hhh888
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: DETACHED
    EdgeLocation: us-east-1
    Segment: prod
    Cidrs: [10.0.0.0/16]
  - AttachmentId: attachment-iii999
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-west-2:111111111111:vpc/vpc-iii999
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-west-2
    Segment: non-prod
    Cidrs: [10.0.1.0/24]

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
      "Resource": "arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-pqr678"
    }
  ]
}
```

Core network policy (segment-actions):

  - segment: prod
    share-with: [prod]
  - segment: non-prod
    share-with: [non-prod]
