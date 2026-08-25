# Diagnostic commands — CloudFormation drift

Canonical command script for each diagnostic step. Use the exact
flags and `--query` filters below; the queries are tuned to surface
the actionable fields only.

## 1. Capture the drift signal

```bash
# Identify the stack and its drift status:
aws cloudformation describe-stacks --stack-name <name> \
  --query 'Stacks[0].{name:StackName,status:StackStatus,drift:StackDriftStatus,lastDetection:LastDriftDetectionDateTime,role:RoleArn}' \
  --output table

# If StackDriftStatus is stale (LastDriftDetectionDateTime older than 24h),
# run a fresh detection (Step 2).
```

## 2. Run / refresh drift detection

```bash
# Start a new drift detection:
DETECTION_ID=$(aws cloudformation detect-stack-drift --stack-name <name> \
  --query 'StackDriftDetectionId' --output text)

# Poll until DetectionStatus is DETECTION_COMPLETE:
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DETECTION_ID \
  --query '{status:DetectionStatus, drift:StackDriftStatus, detected:Timestamp, stack:StackName}'

# DetectionStatus values:
#   DETECTION_IN_PROGRESS  -> keep polling
#   DETECTION_COMPLETE     -> read results (Step 3)
#   DETECTION_FAILED       -> one or more resource types unsupported; see NOT_CHECKED
```

For nested stacks, run drift detection on each child stack via its
ARN (found in the parent's `describe-stack-resources` for
`AWS::CloudFormation::Stack` resources).

For CDK stacks, additionally run `cdk drift <stack-name>` and compare
the construct-level output to the CloudFormation resource-level
output.

## 3. Read drift details per resource

```bash
# All drifted resources (non-IN_SYNC):
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus!=`IN_SYNC`].{logical:LogicalResourceId,physical:PhysicalResourceId,type:ResourceType,status:ResourceDriftStatus,diffs:PropertyDifferences}' \
  --output table

# Filter to MODIFIED only:
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus==`MODIFIED`].{logical:LogicalResourceId,physical:PhysicalResourceId,diffs:PropertyDifferences[].{path:PropertyPath,expected:ExpectedValue,actual:ActualValue,type:DifferenceType}}' \
  --output table

# Filter to DELETED only:
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus==`DELETED`].{logical:LogicalResourceId,physical:PhysicalResourceId,type:ResourceType}' \
  --output table
```

## 4. Forensic walk — who changed it?

```bash
# CloudTrail lookup for the specific physical resource (last 30 days):
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<PhysicalResourceId> \
  --start-time $(date -u -v-30d +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT23:59:59Z) \
  --query 'Events[?EventName!=`Describe*` && EventName!=`List*` && EventName!=`Get*`].{event:EventName,source:EventSource,time:EventTime,user:Username,ip:CloudTrailEvent}' \
  --output table

# AWS Config timeline for property-level forensic diff:
aws configservice get-resource-config-history \
  --resource-type <ResourceType e.g. AWS::S3::Bucket> \
  --resource-id <PhysicalResourceId> \
  --limit 10 \
  --query 'configurationItems[].{capture:captureTime,version:configurationStateId,arn:arn, status:configurationItemStatus}' \
  --output table

# Cross-reference AWS Config rules for the resource:
aws configservice get-compliance-details-by-resource \
  --resource-type <ResourceType> \
  --resource-id <PhysicalResourceId> \
  --query 'ComplianceDetails[].{rule:ConfigRuleName,compliance:ComplianceType}'
```

## 5. Assess update impact (immutable properties)

```bash
# Create a no-op ChangeSet to probe Replacement behaviour:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name drift-impact-probe \
  --change-set-type UPDATE \
  --template-body file://current-template.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name drift-impact-probe \
  --query 'Changes[?ResourceChange.LogicalResourceId==`<drifted-logical-id>`].ResourceChange.{action:Action,replacement:Replacement,scope:Scope,detailed:DetailedStatus}'

# Values:
#   Action: Add | Modify | Remove | Import
#   Replacement: True | False | Conditional
#   Scope: [Properties | Tags | Metadata]
```

Discard the probe ChangeSet after reading:

```bash
aws cloudformation delete-change-set \
  --stack-name <name> --change-set-name drift-impact-probe
```

## 6. Apply resolution

### RESET_TO_DRIFT (accept actual as new template truth)

```bash
# 1. Edit template locally to match actual values.
cfn-lint template-with-drift-accepted.yaml

aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name accept-drift-$(date +%s) \
  --change-set-type UPDATE \
  --template-body file://template-with-drift-accepted.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name accept-drift-<timestamp>

aws cloudformation execute-change-set \
  --stack-name <name> --change-set-name accept-drift-<timestamp>

aws cloudformation wait stack-update-complete --stack-name <name>
```

### REVERT_TO_TEMPLATE (manually restore template value)

No stack update is required; the underlying service's API restores
the template value:

```bash
# Example for S3 bucket policy:
aws s3api put-bucket-policy \
  --bucket <name> \
  --policy file://template-policy.json

# Example for RDS instance identifier rename:
aws rds modify-db-instance \
  --db-instance-identifier <actual-id> \
  --new-db-instance-identifier <template-id> \
  --apply-immediately
```

### IMPORT (bring out-of-band resource under stack management)

```bash
# 1. Generate resources-to-import JSON:
cat > resources-to-import.json <<EOF
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "<LogicalId>",
    "ResourceIdentifier": {"BucketName": "<actual-bucket-name>"}
  }
]
EOF

# 2. Lint the template that declares the resource:
cfn-lint template-with-resource.yaml

# 3. Create and review the IMPORT change set:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name import-<resource>-$(date +%s) \
  --change-set-type IMPORT \
  --resources-to-import file://resources-to-import.json \
  --template-body file://template-with-resource.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name import-<resource>-<timestamp>

# Expect Action: Import with no Replacement.

aws cloudformation execute-change-set \
  --stack-name <name> --change-set-name import-<resource>-<timestamp>

aws cloudformation wait stack-import-complete --stack-name <name>
```

### REMOVE_FROM_TEMPLATE

```bash
# 1. Delete the resource declaration from the template.
# 2. If the physical resource should persist, add DeletionPolicy: Retain.
cfn-lint template-with-resource-removed.yaml

aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name remove-<resource>-$(date +%s) \
  --change-set-type UPDATE \
  --template-body file://template-with-resource-removed.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name remove-<resource>-<timestamp>

aws cloudformation execute-change-set \
  --stack-name <name> --change-set-name remove-<resource>-<timestamp>
```

## 7. Verify resolution

```bash
# Re-run drift detection; expect StackDriftStatus IN_SYNC.
DETECTION_ID=$(aws cloudformation detect-stack-drift --stack-name <name> \
  --query 'StackDriftDetectionId' --output text)

aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DETECTION_ID \
  --query '{status:DetectionStatus, drift:StackDriftStatus, detected:Timestamp}'

# Confirm per-resource:
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus!=`IN_SYNC`]'
# Expect empty list when fully resolved.
```

## 8. Prevent recurrence

### IAM deny policy with `aws:CalledViaFirst`

```bash
# Attach to principals that should not make direct changes:
cat > deny-direct-mutation.json <<EOF
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
      "Resource": "arn:aws:s3:::<cfn-managed-bucket>",
      "Condition": {
        "StringNotEquals": {
          "aws:CalledViaFirst": "cloudformation.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name <role-name> \
  --policy-name DenyDirectMutation \
  --policy-document file://deny-direct-mutation.json
```

### Conformance Pack deployment

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name cfn-drift-detection \
  --template-body file://conformance-pack.yaml \
  --delivery-s3-bucket <config-logging-bucket>
```

Where `conformance-pack.yaml` declares the
`cloudformation-stack-drift-detection-check` managed rule scoped to
`AWS::CloudFormation::Stack`.

## 9. Resource import flow — full CLI sequence (moved from SKILL.md Step 5)

**Resource import flow (high-level):**

```bash
# 1. Generate the resources-to-import JSON:
cat > resources-to-import.json <<EOF
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "MyBucket",
    "ResourceIdentifier": { "BucketName": "my-existing-bucket" }
  }
]
EOF

# 2. Create an IMPORT change set:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name import-bucket \
  --change-set-type IMPORT \
  --resources-to-import file://resources-to-import.json \
  --template-body file://template-with-bucket.yaml \
  --capabilities CAPABILITY_IAM

# 3. Review and execute:
aws cloudformation describe-change-set --stack-name <name> --change-set-name import-bucket
aws cloudformation execute-change-set --stack-name <name> --change-set-name import-bucket
```
