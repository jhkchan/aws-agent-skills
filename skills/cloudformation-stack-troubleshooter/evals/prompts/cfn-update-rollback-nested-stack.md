# Eval prompt: cfn-update-rollback-nested-stack

Diagnose the following CloudFormation stack failure. Walk the
UPDATE_ROLLBACK_FAILED decision tree and emit the standard VERDICT
block.

## Scenario

A CloudFormation parent stack `platform-root` in `us-east-1` ends in
`UPDATE_ROLLBACK_FAILED` after a failed update that modified the
`CIDR` block of a VPC declared inside a nested child stack.

## Known facts

- `describe-stacks` for `platform-root` shows:
  - `StackStatus: UPDATE_ROLLBACK_FAILED`
- `describe-stack-events` for `platform-root` shows the
  `NetworkStack` resource (`AWS::CloudFormation::Stack`) with:
  - `ResourceStatus: UPDATE_ROLLBACK_FAILED`
  - `ResourceStatusReason: "Embedded stack
    arn:aws:cloudformation:us-east-1:111111111111:stack/platform-root-NetworkStack-abc/def
    was not successfully updated: The following resource(s) failed
    to update: [VPC]."`
  - `PhysicalResourceId:
    arn:aws:cloudformation:us-east-1:111111111111:stack/platform-root-NetworkStack-abc/def`
- `describe-stacks` on the nested child stack
  (`platform-root-NetworkStack-abc`) shows:
  - `StackStatus: UPDATE_ROLLBACK_FAILED`
  - Its `VPC` resource (`AWS::EC2::VPC`) failed because `CidrBlock`
    is immutable on an existing VPC.
- No other resources in the parent stack failed.

## Symptom

The operator needs to recover the parent stack to a state where it can
be updated again, and understand why retries of `update-stack` are
rejected.
