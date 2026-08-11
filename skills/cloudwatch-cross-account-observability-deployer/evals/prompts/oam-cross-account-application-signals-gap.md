# Eval prompt: oam-cross-account-application-signals-gap

Diagnose why cross-account Application Signals metrics are missing
in the monitoring account even though the OAM link includes the
resource type. Walk the pre-flight checks and emit the standard
VERDICT block.

## Scenario

An operator wants cross-account Application Signals service maps
in monitoring account `111122223333`. Source account
`444455556666` has the OAM link with
`AWS::ApplicationSignals::Service` in `ResourceTypes`, and the
sink policy allows it. However, `aws application-signals
list-services` in the source account returns an empty list —
Application Signals is not yet enabled on the checkout ECS
workload.

## Known facts

- **Monitoring account:** `111122223333` (us-east-1).
- **Source account:** `444455556666`.
- **OAM link:** exists; includes
  `AWS::ApplicationSignals::Service` in `ResourceTypes`.
- **Sink policy:** allows `AWS::ApplicationSignals::Service`
  for `444455556666`.
- **Source Application Signals:** `aws application-signals
  list-services` returns `[]` — Application Signals is NOT
  enabled on the checkout ECS workload.

## Symptom

The `AWS/ApplicationSignals` namespace is empty in the monitoring
account. The operator expects the service map to populate once
the source workload is discovered.
