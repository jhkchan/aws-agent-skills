# Eval prompt: update-rollback-failed-needs-continue

Diagnose the CloudFormation stack rollback failure for the following
stack. Walk the rollback-focused diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-iam-roles` is stuck in `UPDATE_ROLLBACK_FAILED`. The
update changed the `Path` property of an IAM Role from `/old-path/` to
`/service/`. This is a Replacement operation. The new role was created
but the old role couldn't be deleted because it's still attached to an
instance profile.

```text
StackName: prod-iam-roles
StackStatus: UPDATE_ROLLBACK_FAILED

Failed resource:
  LogicalResourceId: AppServiceRole
  ResourceType: AWS::IAM::Role
  ResourceStatus: DELETE_FAILED
  ResourceStatusReason: "Cannot delete entity: Role is attached to
    instance profile AppServiceInstanceProfile"

IAM context:
  - AppServiceRole (old, /old-path/): exists, has
    AWSLambdaBasicExecutionRole attached
  - AppServiceInstanceProfile: contains AppServiceRole
  - AppServiceRole (new, /service/): created successfully
    during the update

Template summary shows:
  AWS::IAM::Role UpdateBehavior: Replacement
  (Path is an immutable property — changing it triggers replacement)

Stack policy: (none)
Drift: (none detected)
Nested stacks: (none)
```

Changing the IAM Role `Path` triggers a replacement (the old role is
deleted, a new one is created). The old role's deletion fails because
it's still attached to an instance profile. Identify the layer and
recommend the fix.
