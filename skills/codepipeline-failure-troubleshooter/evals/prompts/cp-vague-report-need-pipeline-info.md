# Eval prompt: cp-vague-report-need-pipeline-info

Diagnose the following CodePipeline report. Walk the Step 0 signal
check and emit the standard VERDICT block.

## Scenario

A user reports: "our CI/CD pipeline is broken, the build keeps
failing." They mention it is "the prod pipeline" but provide no
further detail.

## Known facts

- The user references "the prod pipeline" but no pipeline name or
  ARN.
- No region provided (default region may not be the prod region).
- No pipeline execution ID provided.
- No failed stage or action name provided.
- No `lastStatusChangeReason` or `externalExecutionSummary` provided.
- No CodeBuild build ID or logs provided.

## Symptom

The user expects a diagnosis but has provided insufficient identifying
information to walk the decision tree.
