# Eval prompt: cfn-vague-report-need-stack-info

Diagnose the following CloudFormation report. Walk the Step 0 signal
check and emit the standard VERDICT block.

## Scenario

A user reports: "my CloudFormation deployment is broken, the stack
keeps failing." They mention it is a "prod stack" but provide no
further detail.

## Known facts

- The user references "a prod stack" but no stack name or ARN.
- No region provided (default region may not be the prod region).
- No `StackStatus` provided.
- No `ResourceStatusReason` or failing logical id provided.
- No template or recent ChangeSet details provided.

## Symptom

The user expects a diagnosis but has provided insufficient identifying
information to walk the decision tree.
