# Eval prompt: cw-vague-report-need-namespace

Diagnose the following CloudWatch metric report. Walk the Step 0
signal check and emit the standard VERDICT block.

## Scenario

A user reports: "my CloudWatch metric is missing, the dashboard is
empty."

## Known facts

- No namespace provided.
- No metric name provided.
- No dimensions provided.
- No resource identified.
- No expected vs observed value provided.
- No alarm state mentioned.

## Symptom

The user expects a diagnosis but has provided insufficient identifying
information to walk the decision tree.
