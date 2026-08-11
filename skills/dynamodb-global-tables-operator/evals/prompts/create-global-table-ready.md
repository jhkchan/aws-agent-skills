# Eval prompt: create-global-table-ready

Plan the following DynamoDB Global Tables creation. Run the pre-check
gate and emit the standard VERDICT block.

## Scenario

We want to create a new DynamoDB Global Table named `sessions-prod`
with replicas in `us-east-1` and `eu-west-1`.

## Known facts

- Identical empty tables have been created in both regions:
  - `describe-table` (us-east-1): `TableStatus: ACTIVE`, key schema
    `[{AttributeName: sessionId, KeyType: HASH}]`, `AttributeType: S`,
    `BillingMode: PAY_PER_REQUEST`, `ItemCount: 0`
  - `describe-table` (eu-west-1): `TableStatus: ACTIVE`, key schema
    `[{AttributeName: sessionId, KeyType: HASH}]`, `AttributeType: S`,
    `BillingMode: PAY_PER_REQUEST`, `ItemCount: 0`
- `describe-global-table --global-table-name sessions-prod` returns
  `GlobalTableNotFoundException`
- IAM simulation: caller role has `dynamodb:CreateGlobalTable`
- Neither table has any items
- Neither table has a global table association

## Desired operation

Create the `sessions-prod` global table linking us-east-1 and eu-west-1.
