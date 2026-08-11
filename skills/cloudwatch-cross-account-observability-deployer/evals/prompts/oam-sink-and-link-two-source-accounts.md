# Eval prompt: oam-sink-and-link-two-source-accounts

Create a CloudWatch cross-account observability topology with an
OAM sink and two source accounts. Walk the pre-flight checks and
emit the standard VERDICT block (MONITORING_ACCOUNT, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

## Scenario

An operator wants to set up CloudWatch cross-account observability
in `us-east-1`. Monitoring account `111122223333` hosts the sink.
Source accounts `444455556666` (checkout) and `777788889999`
(payments) should share metrics, logs, traces, and Application
Signals data.

## Known facts

- **Monitoring account:** `111122223333` (us-east-1).
- **Source accounts:** `444455556666` (checkout),
  `777788889999` (payments).
- **Metrics to share:** `AWS/EC2`, `AWS/ECS`, `AWS/Lambda`,
  `AWS/ApplicationSignals`.
- **Log groups to share:** `/aws/ecs/prod-app`,
  `/aws/lambda/payments-api`.
- **X-Ray services to share:** `checkout`, `payments`.
- **Application Signals:** enabled in each source account for
  ECS workloads (`list-services` returns both services).
- **Source IAM:** each source has an `OAMLinkRole` with
  `oam:CreateLink` on the sink ARN (once created).
- **Sink policy:** must list both source account principals.

## Symptom

The operator needs the exact `create-sink`, `put-sink-policy`,
and `create-link` (run from each source) CLI sequences, plus
verification that data flows in the monitoring account.
