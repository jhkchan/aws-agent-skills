# Drift types and resolution — full decision matrix

This reference expands the SKILL.md drift classification with the full
per-type decision matrix, immutable-property tables per resource, and
worked examples for each resolution strategy. Load when diagnosing a
specific drift type in depth.

## Drift type decision matrix

### MODIFIED — property changed outside CloudFormation

**Detection surface:**

```bash
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus==`MODIFIED`]'
```

**Output shape:**

```json
{
  "StackResourceDriftStatus": "MODIFIED",
  "LogicalResourceId": "LogsBucket",
  "PhysicalResourceId": "logging-stack-logsbucket-abc",
  "ResourceType": "AWS::S3::Bucket",
  "PropertyDifferences": [
    {
      "PropertyPath": "/BucketPolicy/Document/Statement/0/Principal",
      "ExpectedValue": {"Service": "logging.us-east-1.amazonaws.com"},
      "ActualValue": {"AWS": "arn:aws:iam::111122223333:root"},
      "DifferenceType": "NOT_EQUAL"
    }
  ]
}
```

**Sub-categories by `DifferenceType`:**

| `DifferenceType` | Meaning | Default resolution |
|---|---|---|
| `NOT_EQUAL` | Property value differs | `RESET_TO_DRIFT` (accept actual) or `REVERT_TO_TEMPLATE` |
| `ADD` | Property exists in actual but not template | `RESET_TO_DRIFT` (extend template) or `REVERT_TO_TEMPLATE` (remove) |
| `REMOVE` | Property exists in template but not actual | `RESET_TO_DRIFT` (remove from template) or `REVERT_TO_TEMPLATE` (recreate) |
| `EXACT` | No difference (only appears in API response, never in drift) | n/a |

**Immutable-property table (top resources):**

| Resource | Immutable properties that trigger Replacement |
|---|---|
| `AWS::S3::Bucket` | `BucketName` |
| `AWS::DynamoDB::Table` | `TableName`, `KeySchema` (key attributes only), `AttributeDefinitions` (for keys), `BillingMode` (PAY_PER_REQUEST ↔ PROVISIONED requires replacement in some cases) |
| `AWS::RDS::DBInstance` | `DBInstanceIdentifier`, `AllocatedStorage` (decrease), `Engine`, `DBInstanceClass` (some changes), `StorageType` (some changes) |
| `AWS::RDS::DBCluster` | `DBClusterIdentifier`, `Engine`, `DBClusterInstanceClass` (Aurora) |
| `AWS::IAM::Role` | `RoleName` |
| `AWS::IAM::User` | `UserName` |
| `AWS::IAM::Group` | `GroupName` |
| `AWS::IAM::Policy` | `PolicyName` |
| `AWS::EC2::Instance` | `InstanceType` (depends), `ImageId`, `KeyName`, `SubnetId` |
| `AWS::EC2::VPC` | `CidrBlock` |
| `AWS::EC2::Subnet` | `CidrBlock`, `VpcId`, `AvailabilityZone` |
| `AWS::Lambda::Function` | `FunctionName`, `Role` (some cases), `Runtime` (some), `PackageType` |
| `AWS::SQS::Queue` | `QueueName` |
| `AWS::Logs::LogGroup` | `LogGroupName` |
| `AWS::Kinesis::Stream` | `Name`, `ShardCount` (unless on-demand) |
| `AWS::SNS::Topic` | `TopicName` |
| `AWS::ECS::Cluster` | `ClusterName` |
| `AWS::ECS::Service` | `ServiceName`, `Cluster` (some cases) |
| `AWS::ElasticLoadBalancingV2::LoadBalancer` | `Name`, `Type` |
| `AWS::ElasticLoadBalancingV2::TargetGroup` | `Name`, `Port`, `Protocol`, `VpcId` |
| `AWS::AutoScaling::AutoScalingGroup` | `AutoScalingGroupName` |
| `AWS::KMS::Key` | `KeySpec`, `KeyUsage`, `Origin` |

**Resolution selection rule:**

1. If the drifted property is in the immutable list → default to
   `REVERT_TO_TEMPLATE` (manually restore the original value). Only
   use `RESET_TO_DRIFT` if Replacement is acceptable.
2. If the CloudTrail actor is unknown or the change appears
   malicious → `REVERT_TO_TEMPLATE` always.
3. If the change is intentional and the property is mutable →
   `RESET_TO_DRIFT` (update template to match actual).
4. If the change is in a tag or non-impacting metadata →
   `RESET_TO_DRIFT` (low cost, eliminates drift noise).

**Worked example — REVERT_TO_TEMPLATE on immutable property:**

A `AWS::RDS::DBInstance` `OrdersDB` has a MODIFIED drift on
`DBInstanceIdentifier` (operator renamed the instance out-of-band from
`orders-db-prod` to `orders-db-prod-v2`). `DBInstanceIdentifier` is
immutable, so `update-stack` will trigger Replacement (delete +
recreate). The operator does not want data loss.

Resolution: `REVERT_TO_TEMPLATE` — manually rename the instance back
via `aws rds modify-db-instance --db-instance-identifier
orders-db-prod-v2 --new-db-instance-identifier orders-db-prod` (RDS
supports renaming). After rename succeeds, run `detect-stack-drift`;
status returns `IN_SYNC`. Then attach a deny policy on
`rds:ModifyDBInstance` scoped to the instance, conditioned on
`aws:CalledViaFirst != cloudformation.amazonaws.com`.

### DELETED — resource deleted outside CloudFormation

**Detection surface:** same `describe-stack-resource-drifts` with
`ResourceDriftStatus: DELETED`.

**Sub-categories:**

| Scenario | Resolution |
|---|---|
| Resource deleted manually; nothing in the stack depends on it | `update-stack` to recreate, or `REMOVE_FROM_TEMPLATE` if no longer needed |
| Resource deleted manually; downstream stack resources depend on it (references via `Ref` / `GetAtt`) | `update-stack` to recreate first; downstream resources will recover |
| Resource deleted by another stack (cross-stack `Exports` collision) | Escalate — the deletion is owned by another stack; coordinate with that stack's owner |
| Resource deleted intentionally; should remain gone | `REMOVE_FROM_TEMPLATE` and `update-stack`; consider `DeletionPolicy: Retain` was the intent |
| Resource type does not support drift detection (NOT_CHECKED) | Use AWS Config to detect the deletion; not visible in CloudFormation drift |

**Worked example — DELETED on Lambda function:**

A `AWS::Lambda::Function` `ProcessorLambda` reports `DELETED`. The
physical function was removed via console by another operator. Several
`AWS::Events::Rule` resources in the stack reference it as a target.

Resolution:

1. Confirm via CloudTrail `lookup-events` that the function was
   deleted intentionally.
2. If intentional, `REMOVE_FROM_TEMPLATE` and update the Events rules
   to remove the target.
3. If unintentional, `update-stack` to recreate — CloudFormation
   provisions a new Lambda function with the same logical id and
   template configuration.
4. Verify downstream Events rules recover (next event invocation
   succeeds).

### ADDITION — new resource not in stack

**Detection surface:** CloudFormation drift detection does NOT surface
`ADDITION` directly — drift detection compares each resource declared
in the template to its actual state. An out-of-band resource that is
not in the template is invisible to drift detection. ADDITION drifts
are surfaced via:

- **AWS Config** (`list-discovered-resources`) — account-wide inventory
  that can be cross-referenced against the stack's
  `describe-stack-resources`.
- **IaC Generator** (`create-generated-template`) — scans the account
  and produces template fragments for resources not under stack
  management.
- **Manual discovery** — operator knows a resource exists that should
  be in the stack.

**Sub-categories:**

| Scenario | Resolution |
|---|---|
| Resource overlaps with stack's responsibility (e.g., a bucket that should be managed by the stack) | `IMPORT` to bring under management |
| Resource is intentionally unmanaged (e.g., a separate team owns it) | Ignore — attach an annotation in a CMDB |
| Resource is a duplicate (e.g., console-created copy of a stack-managed resource) | Delete the out-of-band resource; do not import |

**Worked example — IMPORT of out-of-band bucket:**

Operator discovers bucket `app-uploads-2026` exists in the account and
should be managed by the `app-storage` stack.

1. Capture the bucket's current properties (Config or
   `s3api get-bucket-*` calls).
2. Author the template fragment declaring `MyUploadsBucket` with
   properties matching the actual bucket.
3. Generate the `resources-to-import.json` payload:

```json
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "MyUploadsBucket",
    "ResourceIdentifier": {"BucketName": "app-uploads-2026"}
  }
]
```

4. Create and execute an IMPORT change set:

```bash
aws cloudformation create-change-set \
  --stack-name app-storage \
  --change-set-name import-uploads-bucket \
  --change-set-type IMPORT \
  --resources-to-import file://resources-to-import.json \
  --template-body file://template-with-bucket.yaml
aws cloudformation describe-change-set \
  --stack-name app-storage --change-set-name import-uploads-bucket
aws cloudformation execute-change-set \
  --stack-name app-storage --change-set-name import-uploads-bucket
```

5. Verify via `describe-stack-resources` that `MyUploadsBucket` now
   maps to `app-uploads-2026` with status `IMPORT_COMPLETE`.

### NOT_CHECKED — drift detection unsupported

**Detection surface:** `describe-stack-resource-drifts` shows
`ResourceDriftStatus: NOT_CHECKED` for resource types that do not
support drift detection (e.g., some third-party registered types,
`AWS::CloudFormation::WaitConditionHandle`, resources using
`Default` values in extensions).

**Resolution:** pair AWS Config with the
`cloudformation-stack-drift-detection-check` managed rule on a
schedule. For specific unsupported resources, author a custom Config
rule that checks the resource's actual state against the template.

## Resolution strategy playbook

### RESET_TO_DRIFT

Accept the out-of-band change as the new template truth.

```bash
# 1. Update the template to match actual values.
# 2. Create and review a ChangeSet:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name accept-drift-<timestamp> \
  --change-set-type UPDATE \
  --template-body file://template-with-drift-accepted.yaml \
  --capabilities CAPABILITY_IAM
aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name accept-drift-<timestamp>
# Confirm Replacement False for the drifted resource.
aws cloudformation execute-change-set \
  --stack-name <name> --change-set-name accept-drift-<timestamp>
# 3. Re-run drift detection; expect IN_SYNC.
```

### REVERT_TO_TEMPLATE

Manually restore the resource to match the template. No stack update
is required.

```bash
# 1. Identify the actual value via Config or describe.
# 2. Use the underlying service's API to restore the template value.
#    Example for S3 bucket policy:
aws s3api put-bucket-policy --bucket <name> --policy file://template-policy.json
# 3. Re-run drift detection; expect IN_SYNC.
DETECTION_ID=$(aws cloudformation detect-stack-drift --stack-name <name> \
  --query 'StackDriftDetectionId' --output text)
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DETECTION_ID
```

### IMPORT

Bring an out-of-band resource under stack management. See the
ADDITION worked example above.

### REMOVE_FROM_TEMPLATE

Remove the drifted resource from the template entirely.

```bash
# 1. Delete the resource declaration from the template.
# 2. If the physical resource should persist, set DeletionPolicy: Retain
#    in the template before this update.
# 3. Create and execute a ChangeSet:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name remove-resource-<timestamp> \
  --change-set-type UPDATE \
  --template-body file://template-with-resource-removed.yaml
aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name remove-resource-<timestamp>
aws cloudformation execute-change-set \
  --stack-name <name> --change-set-name remove-resource-<timestamp>
```

### ESCALATE_TO_OWNER

Surface the CloudTrail actor and Config timeline; route to the
resource owner. Use this when the drift is in another team's scope
(e.g., a security team owns the bucket policy, an SRE team owns the
IAM roles) or when remediation requires approval (e.g., a production
database rename).

## Drift prevention playbook

### IAM policy with `aws:CalledViaFirst`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDirectMutationOnCfnManagedResources",
      "Effect": "Deny",
      "Action": [
        "s3:PutBucketPolicy",
        "s3:DeleteBucket",
        "s3:PutEncryptionConfiguration",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": "arn:aws:s3:::my-cfn-managed-bucket",
      "Condition": {
        "StringNotEquals": {
          "aws:CalledViaFirst": "cloudformation.amazonaws.com"
        }
      }
    }
  ]
}
```

Apply to all principals that should not make direct changes. The
CloudFormation execution role inherits the context key correctly
when CloudFormation makes the call.

### CloudFormation Hook (prevent deployment-time non-compliance)

Author a Hook targeting the resource type at
`CREATE_PRE_DEPLOYMENT` / `UPDATE_PRE_DEPLOYMENT`. Hooks fire on
stack updates only — they do not prevent out-of-band changes, but
they ensure that the next stack update is compliant with the
organization's policy (e.g., requiring encryption on all buckets).

### Conformance Pack

```yaml
# Conformance pack with drift detection rule
Resources:
  DriftDetectionRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: cloudformation-stack-drift-detection-check
      Source:
        Owner: AWS
        SourceIdentifier: CLOUDFORMATION_STACK_DRIFT_DETECTION_CHECK
      Scope:
        ComplianceResourceTypes:
          - AWS::CloudFormation::Stack
```

Deploy via `aws configservice put-conformance-pack`. Pair with SNS +
Lambda for auto-detection and remediation.

## Related patterns

- **Drift on nested stacks** — drill into the child stack via its ARN;
  the parent's `AWS::CloudFormation::Stack` resource carries the
  child's aggregate status.
- **CDK drift** — use `cdk drift <stack-name>` for construct-level
  overview; cross-reference CloudFormation for resource-level detail.
- **Drift after stack delete on Retain resources** — track via AWS
  Config; CloudFormation no longer knows about the resource.
