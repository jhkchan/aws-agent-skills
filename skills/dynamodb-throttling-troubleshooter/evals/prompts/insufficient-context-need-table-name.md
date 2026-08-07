# Eval prompt: insufficient-context-need-table-name

Diagnose the following DynamoDB throttling report. The user has provided
only a vague symptom — no table name, no region, no CloudWatch metrics,
no error string, no access pattern. Emit the standard VERDICT block. If
the diagnostic tree cannot proceed without more evidence, emit
NEED_MORE_INFO and list the missing inputs.

## Scenario

A user reports: "my DynamoDB is throttling, the application is throwing
errors." They mention the application name `checkout-service` but do not
provide any further identifying information.

## What the user has provided

- Application name: `checkout-service`
- Symptom: "DynamoDB is throttling"

## What the user has NOT provided

- The DynamoDB table name.
- The AWS region.
- The throttle error string (`ProvisionedThroughputExceededException` vs
  `RequestLimitExceeded` vs something else).
- The CloudWatch `ThrottledRequests` pattern (spike vs sustained, read vs
  write).
- The table's billing mode (PROVISIONED vs ON_DEMAND).
- Whether GSIs exist on the table.
- The access pattern (GetItem / Query / Scan / BatchGetItem).
- The partition key distribution.
- Whether a recent traffic change or deployment coincides with the
  throttling.
- Whether the throttling is intermittent or sustained.
