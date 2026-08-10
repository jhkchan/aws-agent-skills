# Eval prompt: cfn-create-iam-capability-missing

Diagnose the following CloudFormation stack failure. Walk the
CREATE_FAILED decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CloudFormation stack `app-platform` in `us-east-1` failed to create.
The operator ran:

```
aws cloudformation create-stack --stack-name app-platform \
  --template-body file://template.yaml \
  --role-arn arn:aws:iam::111111111111:role/cfn-exec
```

No `--capabilities` flag was passed. The template declares an
`AWS::IAM::Role` named `TaskRole`.

## Known facts

- `describe-stacks` for `app-platform` shows:
  - `StackStatus: ROLLBACK_COMPLETE`
  - `StackStatusReason: "The following resource(s) failed to create:
    [TaskRole]."`
- `describe-stack-events` shows the `TaskRole` resource with:
  - `ResourceStatus: CREATE_FAILED`
  - `ResourceStatusReason: "Requires capabilities : [CAPABILITY_IAM].
    User requested no capabilities."`
- No other `CREATE_FAILED` events appear in `describe-stack-events`
  (TaskRole is the only failure).
- The `cfn-exec` execution role has a broad administrator policy
  attached — IAM permissions themselves are not the issue.

## Symptom

Every re-attempt to `create-stack` with the same command fails
identically; the stack ends in `ROLLBACK_COMPLETE`.
