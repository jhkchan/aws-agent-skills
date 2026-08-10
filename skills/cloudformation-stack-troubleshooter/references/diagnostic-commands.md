# CloudFormation diagnostic command reference

Canonical command script for the `cloudformation-stack-troubleshooter`
skill. Run these in order; each command's output narrows the decision
tree.

## 1. Identify the failing stack and its status

```bash
aws cloudformation describe-stacks --stack-name <name> \
  --query 'Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,role:RoleArn,capabilities:Capabilities}'
```

If you only have a partial stack name, list stacks in failing states:

```bash
aws cloudformation list-stacks \
  --stack-status-filter CREATE_FAILED UPDATE_FAILED UPDATE_ROLLBACK_FAILED \
                           DELETE_FAILED ROLLBACK_COMPLETE UPDATE_ROLLBACK_COMPLETE \
  --query 'StackSummaries[*].{name:StackName,status:StackStatus,reason:StackStatusReason}'
```

## 2. Find the failing resource(s)

The first `CREATE_FAILED` / `UPDATE_FAILED` by timestamp is the cause;
the rest are cascade.

```bash
# Earliest CREATE_FAILED (root cause during a failed CREATE):
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'reverse(StackEvents[?ResourceStatus==`CREATE_FAILED`])[-1].{logical:LogicalResourceId,type:ResourceType,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table

# All CREATE_FAILED resources (to see the cascade):
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].{logical:LogicalResourceId,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table

# UPDATE_FAILED / UPDATE_ROLLBACK_FAILED events:
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'StackEvents[?ResourceStatus==`UPDATE_FAILED` || ResourceStatus==`UPDATE_ROLLBACK_FAILED`].{logical:LogicalResourceId,status:ResourceStatus,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table

# DELETE_FAILED events:
aws cloudformation describe-stack-events --stack-name <name> \
  --query 'StackEvents[?ResourceStatus==`DELETE_FAILED` || ResourceStatus==`DELETE_SKIPPED`].{logical:LogicalResourceId,status:ResourceStatus,reason:ResourceStatusReason,ts:Timestamp}' \
  --output table
```

## 3. Read physical resource state

```bash
aws cloudformation describe-stack-resources --stack-name <name> \
  --logical-resource-id <logical-id> \
  --query 'StackResources[0].{logical:LogicalResourceId,type:ResourceType,physical:PhysicalResourceId,status:ResourceStatus}'
```

## 4. Review the ChangeSet (for UPDATE_FAILED)

```bash
# List recent change sets:
aws cloudformation list-change-sets --stack-name <name> \
  --query 'Summaries[*].{name:ChangeSetName,id:ChangeSetId,status:Status,creation:CreationTime}'

# Describe a change set — focus on Action and Replacement:
aws cloudformation describe-change-set --stack-name <name> \
  --change-set-name <change-set-name> \
  --query 'Changes[*].{logical:ResourceChange.LogicalResourceId,action:ResourceChange.Action,replacement:ResourceChange.Replacement,scope:ResourceChange.Scope,detailed:ResourceChange.DetailedStatus}'
```

If `Replacement: True`, identify which property caused it via `Scope`
and the resource type's documentation (immutable properties).

## 5. Drift detection (for UPDATE surprises)

```bash
# Detect drift on the stack:
aws cloudformation detect-stack-drift --stack-name <name> \
  --query 'StackDriftDetectionId'

# Read the drift status (after detection completes):
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <id>

# List drifted resources:
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?StackResourceDriftStatus==`MODIFIED`].{logical:LogicalResourceId,type:ResourceType,differences:PropertyDifferences}'
```

## 6. For IAM / AccessDenied sub-causes: simulate the execution role

```bash
# Identify the execution role:
aws cloudformation describe-stacks --stack-name <name> \
  --query 'Stacks[0].RoleArn' --output text

# Simulate the action on the resource:
aws iam simulate-principal-policy \
  --policy-source-arn <execution-role-arn> \
  --action-names <service>:<Action> \
  --resource-arns <resource-arn>

# For SCP / permissions boundary blocks, also check:
aws organizations list-policies-for-target --target-id <account-id> \
  --filter SERVICE_CONTROL_POLICY
```

## 7. For S3 bucket DELETE_FAILED: list objects AND versions

```bash
# Current objects:
aws s3api list-objects-v2 --bucket <name> \
  --query 'Contents[*].{key:Key,size:Size}'

# Non-current versions (the usual culprit on versioned buckets):
aws s3api list-object-versions --bucket <name> \
  --query 'Versions[*].{key:Key,versionId:VersionId,isLatest:IsLatest,lastModified:LastModified}'

# Delete markers (also block bucket deletion):
aws s3api list-object-versions --bucket <name> \
  --query 'DeleteMarkers[*].{key:Key,versionId:VersionId}'
```

## 8. For custom resource signal timeout: read the Lambda logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern "ERROR" \
  --start-time <epoch-ms> \
  --limit 50 \
  --query 'events[*].{timestamp:timestamp,message:message}'
```

Look for missing `cfn-response.send(...)` calls or unhandled exceptions
that prevent the function from sending `SUCCESS` to CloudFormation.

## 9. For nested stack failures: drill into the child

```bash
# Identify the nested child stack ARN from the parent's events:
aws cloudformation describe-stack-events --stack-name <parent-name> \
  --query 'StackEvents[?ResourceStatus==`UPDATE_ROLLBACK_FAILED` || ResourceStatus==`CREATE_FAILED`].{logical:LogicalResourceId,physical:PhysicalResourceId,reason:ResourceStatusReason}'

# Diagnose the child independently:
aws cloudformation describe-stacks --stack-name <child-arn>
aws cloudformation describe-stack-events --stack-name <child-arn> \
  --query 'reverse(StackEvents[?ResourceStatus==`UPDATE_FAILED` || ResourceStatus==`CREATE_FAILED`])[-1]'
```

The `PhysicalResourceId` of an `AWS::CloudFormation::Stack` resource
in the parent is the child stack's ARN.

## 10. Recover from UPDATE_ROLLBACK_FAILED

```bash
# Continue the rollback, skipping the resource that cannot roll back:
aws cloudformation continue-update-rollback \
  --stack-name <name> \
  --resources-to-skip <logical-id-of-failing-resource> \
  --query '{id:StackId,status:StackStatus}'

# For nested stacks, skip the nested-stack resource in the PARENT:
aws cloudformation continue-update-rollback \
  --stack-name <parent-name> \
  --resources-to-skip <nested-stack-logical-id>
```

After completion, the stack returns to `UPDATE_ROLLBACK_COMPLETE` and
can be updated again. Skipped resources are now potentially
inconsistent — document and reconcile manually.

## 11. Validate the fix via ChangeSet before applying

```bash
# Lint the fixed template first:
cfn-lint fixed-template.yaml

# Create a ChangeSet against the existing stack (no execution yet):
aws cloudformation create-change-set --stack-name <name> \
  --change-set-name fix-$(date +%s) \
  --template-body file://fixed-template.yaml \
  --capabilities CAPABILITY_IAM

# Review:
aws cloudformation describe-change-set --stack-name <name> \
  --change-set-name <change-set-name> \
  --query 'Changes[*].{logical:ResourceChange.LogicalResourceId,action:ResourceChange.Action,replacement:ResourceChange.Replacement}'

# Execute only after review:
aws cloudformation execute-change-set --stack-name <name> \
  --change-set-name <change-set-name>
```

## 12. Delete a ROLLBACK_COMPLETE stack and recreate

```bash
# A ROLLBACK_COMPLETE stack CANNOT be updated — delete it first:
aws cloudformation delete-stack --stack-name <name>

# Recreate with the fixed template:
aws cloudformation create-stack --stack-name <name> \
  --template-body file://fixed-template.yaml \
  --capabilities CAPABILITY_IAM \
  --role-arn <role-arn>

# Monitor until CREATE_COMPLETE:
aws cloudformation describe-stacks --stack-name <name> \
  --query 'Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason}'
```

## 13. Empty an S3 bucket that blocks DELETE_FAILED (including versions)

```bash
# Empty all current objects:
aws s3 rm s3://<bucket> --recursive

# Empty all versions and delete markers (required for versioned buckets):
aws s3api list-object-versions --bucket <bucket> \
  --query '{versions:Versions,deleteMarkers:DeleteMarkers}' \
  --output json | jq -r '.versions[]?.Key + " " + .versions[]?.VersionId,
                          .deleteMarkers[]?.Key + " " + .deleteMarkers[]?.VersionId' \
  | while read key version; do
      aws s3api delete-object --bucket <bucket> --key "$key" --version-id "$version"
    done

# Retry the stack delete:
aws cloudformation delete-stack --stack-name <name>
```

For repeatable teardowns, add a `Custom::S3Cleanup` (Lambda-backed)
resource to the template that empties the bucket on `Delete`.
