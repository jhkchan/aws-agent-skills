# Eval prompt: sfn-permission-cross-account-sts

Diagnose the following Step Functions execution failure. Walk the
States.Permission decision tree and emit the standard VERDICT block.

## Scenario

A Standard Step Functions workflow in account `111111111111` fails on
the `QueryForeignResource` state with `States.Permission`. State
machine ARN:
`arn:aws:states:us-east-1:111111111111:stateMachine:audit-pipeline`.

## Known facts

- `describe-execution` for the failing execution shows:
  - `status: FAILED`
  - `error: "States.Permission"`
  - `cause: "Is not authorized to perform: sts:AssumeRole on resource
    arn:aws:iam::222222222222:role/foreign-resource-role"`
- `describe-state-machine` shows:
  - `roleArn: arn:aws:iam::111111111111:role/sfn-role`
  - `QueryForeignResource` state uses
    `Resource: arn:aws:states:::aws-sdk:dynamodb:getItem` with
    `Parameters` pointing at a table in account `222222222222` via
    the assumed role `arn:aws:iam::222222222222:role/foreign-resource-role`.
- `aws iam simulate-principal-policy` on
  `arn:aws:iam::111111111111:role/sfn-role` for `sts:AssumeRole` on
  `arn:aws:iam::222222222222:role/foreign-resource-role` returns
  `implicitDeny`.
- `aws iam list-attached-role-policies --role-name sfn-role` shows
  only `AWSLambdaRole` (which grants `lambda:InvokeFunction`, not
  `sts:AssumeRole`).

## Symptom

Every execution of `audit-pipeline` fails on `QueryForeignResource`
with `States.Permission`. The cross-account role
`foreign-resource-role` in account `222222222222` has a trust policy
that DOES permit `arn:aws:iam::111111111111:role/sfn-role` to assume
it — the gap is on the `111111111111` side.
