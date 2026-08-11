# Eval prompt: war-create-workload-all-pillars

Create a production Well-Architected workload. Walk the pre-flight
checks and emit the standard VERDICT block (OPERATION, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES, CONFIRM).

## Scenario

An operator wants to create a Well-Architected Tool workload for
the "checkout-service" microservice in `us-east-1`.

## Known facts

- **Workload name:** `checkout-service`.
- **Description:** "Checkout microservice handling payment
  authorization and order capture".
- **Environment:** `PRODUCTION`.
- **Review owner:** `payments-platform@example.com`.
- **Lenses:** `wellarchitected` and `wellarchitected-prosperity`.
- **Account:** `111122223333`.
- **Regions:** `us-east-1`, `us-west-2`.
- **Pillar IDs:** all six base pillars
  (`operationalExcellence`, `security`, `reliability`,
  `performance`, `costOptimization`, `sustainability`).
- **Prosperity lens:** already imported into the account.
- **Caller permissions:** `wellarchitected:CreateWorkload` and
  `wellarchitected:AssociateLenses`.

## Symptom

The operator needs the exact `create-workload` CLI sequence
with all flags populated, including the Prosperity lens and the
CONFIRM gate.
