# Eval prompt: insufficient-context-blocked

Plan the following DynamoDB Global Tables operation. Run the pre-check
gate and emit the standard VERDICT block.

## Scenario

A user asks: "I need to set up multi-region DynamoDB for disaster
recovery."

## Known facts

- The user did NOT provide:
  - The table name
  - The target regions
  - The billing mode (PROVISIONED or PAY_PER_REQUEST)
  - The key schema
  - Whether the table already exists (single-region)
  - Whether any empty tables have been pre-created
  - The application's failover mechanism
  - The IAM role or permissions

## Desired operation

Plan a global table creation. However, insufficient information was
provided to proceed.
