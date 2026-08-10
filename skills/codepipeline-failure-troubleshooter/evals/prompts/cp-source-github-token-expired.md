# Eval prompt: cp-source-github-token-expired

Diagnose the following CodePipeline execution failure. Walk the
SOURCE_STAGE_FAILED decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CodePipeline `app-cicd` in `us-east-1` fails at the Source stage.
The pipeline uses a GitHub v1 source action configured with a personal
access token stored in Secrets Manager.

## Known facts

- `list-action-executions` for the failing execution shows the Source
  action with:
  - `lastStatus: Failed`
  - `lastStatusChangeReason: "Action execution failed"`
  - `externalExecutionSummary: "Could not authenticate to GitHub"`
- The GitHub connection was last successfully used 92 days ago
  (per the action's `lastStatusChangeAt` timestamp on the last
  successful Source action).
- The PAT in Secrets Manager has a `Credential requires renewal`
  flag in the GitHub security audit log (token expired 2 days ago).
- `get-pipeline` Source action configuration shows
  `Owner: <github-org>`, `Repo: <repo>`, `Branch: main`,
  `OAuthToken: ****` (resolved from a Secrets Manager secret), and
  the v1 `GitHub` action provider.
- No other actions failed in the execution.

## Symptom

Every pipeline execution now fails at the Source stage with the same
"Could not authenticate to GitHub" error.
