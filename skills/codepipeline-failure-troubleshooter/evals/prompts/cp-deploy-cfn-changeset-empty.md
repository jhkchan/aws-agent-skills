# Eval prompt: cp-deploy-cfn-changeset-empty

Diagnose the following CodePipeline execution failure. Walk the
DEPLOY_STAGE_FAILED decision tree and emit the standard VERDICT block.

## Scenario

A CodePipeline `app-cicd` in `us-east-1` fails at the Deploy stage.
The Deploy action is a CloudFormation action with
`ActionMode: CREATE_UPDATE` and change-set processing against the
stack `app-platform`.

## Known facts

- `list-action-executions` shows the Deploy action with:
  - `lastStatus: Failed`
  - `externalExecutionSummary: "ChangeSet is empty"`
- `describe-change-set` for the auto-generated change-set returns:
  - `Status: FAILED`
  - `StatusReason: "The submitted information didn't contain changes.
    Submit fresh information to create a change set."`
  - `Changes: []` (empty)
- The CodeBuild Build action succeeded and produced a `template.yaml`
  output artifact in the pipeline artifact bucket.
- `aws cloudformation get-template --stack-name app-platform` shows
  the currently-deployed template is byte-identical to the Build
  action's output artifact.
- No stack-level `UPDATE_FAILED` event appears in
  `describe-stack-events` for `app-platform` (the change-set never
  executed because it had no changes).
- No prior Build or Source action failed in this execution.

## Symptom

Every pipeline execution now fails at the Deploy stage with the same
"ChangeSet is empty" error, even though the build is producing a
template successfully.
