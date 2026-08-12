# Eval prompt: stack-policy-blocks-rollback

Diagnose the CloudFormation stack rollback failure for the following
stack. Walk the rollback-focused diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-data` is stuck in `UPDATE_ROLLBACK_FAILED`. The rollback
failed because a stack policy blocks updates to the RDS DBInstance
resource. The error in stack events is "Action not allowed by stack
policy."

```text
StackName: prod-data
StackStatus: UPDATE_ROLLBACK_FAILED

Failed resource:
  LogicalResourceId: PrimaryDB
  ResourceType: AWS::RDS::DBInstance
  ResourceStatus: UPDATE_FAILED
  ResourceStatusReason: "Action not allowed by stack policy:
    Update:Replace is denied for resources of type
    AWS::RDS::DBInstance"

Stack policy:
  {
    "Statement": [{
      "Effect": "Deny",
      "Principal": "*",
      "Action": "Update:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ResourceType": ["AWS::RDS::DBInstance"]
        }
      }
    }]
  }

Drift: (none detected)
Nested stacks: (none)
Custom resources: (none)
```

The update that triggered the rollback was attempting to change the
DBInstanceClass from `db.r5.xlarge` to `db.r5.2xlarge`. The rollback
needs to revert to `db.r5.xlarge` but the stack policy blocks the
replacement. Identify the layer and recommend the fix.
