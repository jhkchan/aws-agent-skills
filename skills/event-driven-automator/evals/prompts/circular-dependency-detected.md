# Eval prompt: circular-dependency-detected

Design an EventBridge event-driven workflow for the following
scenario. Emit the standard ARCHITECTURE block (BUS, PATTERN,
TARGETS, RETRY, SAFETY, AUDIT, VERDICT, GAP, TEMPLATE). Include
the circular-dependency check.

Design reference: circular-dependency-detected
Account: 111111111111
Region: us-east-1

Existing rules:
  - rule-A: matches my.app.user event on custom bus "app-events",
    target Lambda-B
  - rule-C: matches my.app.audit event on custom bus "app-events",
    target Lambda-D

Proposed new behavior: Lambda-B publishes my.app.audit. Lambda-D
publishes my.app.user.

Review the topology and emit the standard ARCHITECTURE block.
