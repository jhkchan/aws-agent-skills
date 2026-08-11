# Eval prompt: cfn-drift-vague-report-need-stack-info

Diagnose the following CloudFormation drift report. Walk the
diagnostic decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
RESOLUTION, REMEDIATION).

## Scenario

A user reports: "I think my CloudFormation stack is drifted, can you
check?" They mention it is a "production stack in one of the eastern
regions" but do not provide further details.

## Known facts

- No stack name or ARN provided.
- No region specified (only "an eastern region").
- No `StackDriftStatus` value provided.
- No `describe-stack-resource-drifts` output provided.
- No CloudTrail or Config evidence.

## Symptom

The user is asking for a drift diagnosis but has not provided the
identifying inputs.
