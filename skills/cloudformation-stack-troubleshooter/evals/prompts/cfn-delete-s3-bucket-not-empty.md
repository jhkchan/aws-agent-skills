# Eval prompt: cfn-delete-s3-bucket-not-empty

Diagnose the following CloudFormation stack failure. Walk the
DELETE_FAILED decision tree and emit the standard VERDICT block.

## Scenario

A CloudFormation stack `logging-bucket-stack` in `us-east-1` fails to
delete. The stack contains a single `AWS::S3::Bucket` resource named
`LogsBucket` with `DeletionPolicy: Delete` and versioning enabled.

## Known facts

- `describe-stacks` shows:
  - `StackStatus: DELETE_FAILED`
- `describe-stack-events` shows the `LogsBucket` resource with:
  - `ResourceStatus: DELETE_FAILED`
  - `ResourceStatusReason: "The bucket you tried to delete is not
    empty. You must delete all versions in the bucket."`
- The bucket has versioning enabled (`VersioningConfiguration:
  Status: Enabled`).
- `aws s3api list-objects-v2 --bucket <name>` returns a few current
  objects, and `aws s3api list-object-versions --bucket <name>`
  returns many non-current versions accumulated over months.
- The template `DeletionPolicy` on `LogsBucket` is `Delete` (not
  `Retain`) — so the policy is not the cause.
- No custom resources exist in the stack; no `DELETE_SKIPPED` events
  appear in `describe-stack-events`.

## Symptom

Every `delete-stack` retry fails identically with the same
`DELETE_FAILED` on `LogsBucket`.
