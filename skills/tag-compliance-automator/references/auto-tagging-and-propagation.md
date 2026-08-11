# Auto-Tagging and Tag Propagation Reference

Supplementary reference for the Tag Compliance Automator skill. Use
when building an EventBridge + Lambda auto-tagger, propagating tags
from parent to child resources, or debugging a propagation gap.

## EventBridge rule patterns

### EC2 RunInstances

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com"],
    "eventName": ["RunInstances"]
  }
}
```

### S3 CreateBucket

```json
{
  "source": ["aws.s3"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["s3.amazonaws.com"],
    "eventName": ["CreateBucket"]
  }
}
```

### Lambda CreateFunction

```json
{
  "source": ["aws.lambda"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["lambda.amazonaws.com"],
    "eventName": ["CreateFunction20150331"]
  }
}
```

## Lambda handler: deriving tags from the event

The auto-tagger derives tag values from the CloudTrail event detail:

| Tag key | Derivation source |
|---|---|
| `Environment` | Static map from `userIdentity.accountId` to env |
| `Owner` | `userIdentity.arn` (normalize role sessions via lookup table) |
| `Project` | Static map from account or VPC |
| `CostCenter` | Static map from account |

## EC2-to-child propagation

The `RunInstances` API returns instance IDs, volume IDs, and ENI IDs.
The Lambda must call `ec2:create-tags` on each child resource.

```python
def propagate_to_children(instance_id, tags):
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    for r in desc["Reservations"]:
        for i in r["Instances"]:
            volume_ids = [
                v["Ebs"]["VolumeId"]
                for v in i.get("BlockDeviceMappings", [])
                if "Ebs" in v
            ]
            eni_ids = [
                n["NetworkInterfaceId"]
                for n in i.get("NetworkInterfaces", [])
            ]
            if volume_ids:
                ec2.create_tags(Resources=volume_ids, Tags=tags)
            if eni_ids:
                ec2.create_tags(Resources=eni_ids, Tags=tags)
```

## Propagation coverage matrix

| Parent | Child | API call |
|---|---|---|
| EC2 Instance | EBS volumes | `ec2:create-tags` on `VolumeId` |
| EC2 Instance | ENIs | `ec2:create-tags` on `NetworkInterfaceId` |
| RDS DB Instance | Automated snapshots | `rds:add-tags-to-resource` |
| Lambda Function | Versions, aliases | Automatic (inherit function tags) |
| S3 Bucket | Objects | Not automatic — use Bucket Tagging Set |

## Required IAM permissions for the auto-tagger

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutBucketTagging"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:TagResource"],
      "Resource": "*"
    }
  ]
}
```

## DLQ and idempotency

- Attach an SQS DLQ to the EventBridge target to capture failed events.
- The Lambda must be idempotent: read current tags first, merge deltas,
  only call `create-tags` for missing or corrected keys.
- EventBridge replays events on failure recovery; a non-idempotent
  Lambda may overwrite a corrected value with a stale derived value.

## Common propagation failures

| Failure | Root cause | Fix |
|---|---|---|
| EBS volumes untagged | Lambda not calling `create-tags` on volumes | Add propagation handler (above) |
| ENIs untagged | Lambda not calling `create-tags` on ENIs | Add propagation handler |
| `AccessDenied` on child resources | Lambda role scoped to instances only | Add `ec2:CreateTags` on `volume/*` and `network-interface/*` |
| Tag stamped but Config NON_COMPLIANT | Key casing mismatch | Normalize key name before `create-tags` |
| EventBridge rule fires but Lambda not invoked | Target missing or permission absent | `events:put-targets` + `lambda:AddPermission` for `events.amazonaws.com` |
