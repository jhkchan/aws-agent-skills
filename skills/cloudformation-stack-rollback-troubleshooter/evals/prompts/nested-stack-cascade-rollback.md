# Eval prompt: nested-stack-cascade-rollback

Diagnose the CloudFormation stack rollback failure for the following
stack. Walk the rollback-focused diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-platform` is stuck in `UPDATE_ROLLBACK_FAILED` because
a nested child stack (`NetworkingStack`) is also in
`UPDATE_ROLLBACK_FAILED`. The child's blocking resource is a custom
resource that timed out. The team has been retrying
`continue-update-rollback` on the parent but it keeps failing because
the child is still stuck.

```text
StackName: prod-platform
StackStatus: UPDATE_ROLLBACK_FAILED

Failed resource (parent):
  LogicalResourceId: NetworkingStack
  ResourceType: AWS::CloudFormation::Stack
  ResourceStatus: UPDATE_FAILED
  ResourceStatusReason: "Embedded stack
    arn:aws:cloudformation:us-east-1:111111111111:stack/prod-platform-NetworkingStack-xyz/def-456
    was not successfully updated."

Child stack:
  StackName: prod-platform-NetworkingStack-xyz
  StackStatus: UPDATE_ROLLBACK_FAILED
  Failed resource:
    LogicalResourceId: VpcEndpointCustomResource
    ResourceType: Custom::VpcEndpoint
    ResourceStatus: DELETE_FAILED
    ResourceStatusReason: "Custom Resource timed out waiting for
      provider response (provider Lambda timed out at 10s)."

Operator context: The team has been trying to continue-update-rollback
on the parent stack but it keeps failing because the child is still
stuck.

Stack policy: (none)
Drift: (none detected)
```

The parent's rollback cannot succeed while the child is stuck. The
child must be fixed first (its own `continue-update-rollback`), then
the parent can retry. Identify the layer and recommend the fix.
