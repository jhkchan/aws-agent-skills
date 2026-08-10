# Eval prompt: cp-cross-account-role-trust-expired

Diagnose the following CodePipeline execution failure. Walk the
CROSS_ACCOUNT_ROLE_FAILED decision tree and emit the standard VERDICT
block.

## Scenario

A CodePipeline `app-cicd` in account `111111111111` (`us-east-1`)
fails at the Deploy stage. The Deploy action deploys into account
`222222222222` via the customer-managed role
`arn:aws:iam::222222222222:role/cross-acct-deploy`.

## Known facts

- `list-action-executions` shows the Deploy action with:
  - `lastStatus: Failed`
  - `lastStatusChangeReason: "Action execution failed"`
  - `externalExecutionSummary: "is not authorized to perform:
    sts:AssumeRole on resource
    arn:aws:iam::222222222222:role/cross-acct-deploy"`
- `aws iam get-role --role-name cross-acct-deploy` in account
  `222222222222` shows the `AssumeRolePolicyDocument`:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::111111111111:role/AWSCodePipelineServiceRole-old-pipeline" },
      "Action": "sts:AssumeRole"
    }]
  }
  ```
- `get-pipeline app-cicd` shows the current pipeline service role
  (`metadata.pipelineExecutionRole`) is
  `arn:aws:iam::111111111111:role/AWSCodePipelineServiceRole-app-cicd`.
- The pipeline was renamed from `old-pipeline` to `app-cicd` last
  week, which created a new service role with the matching new name.
- No KMS or bucket policy errors appear in this execution (the assume
  itself never succeeded, so the deploy never reached the artifact
  bucket).

## Symptom

Every cross-account Deploy action now fails immediately with the
`sts:AssumeRole` access-denied error, even though the previous
deployment (before the rename) succeeded.
