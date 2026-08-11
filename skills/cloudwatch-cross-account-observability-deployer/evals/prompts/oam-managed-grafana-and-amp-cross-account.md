# Eval prompt: oam-managed-grafana-and-amp-cross-account

Wire Amazon Managed Grafana and an AMP workspace for cross-account
queries alongside a working OAM topology. Walk the pre-flight
checks and emit the standard VERDICT block.

## Scenario

An operator has a working OAM topology — sink in monitoring
account `111122223333` (us-east-1), two source accounts attached,
metrics / logs / traces / Application Signals flowing. Now the
operator wants to:

1. Wire Amazon Managed Grafana workspace `g-abcdef1234` to query
   via the sink (assume a `GrafanaCrossAccountReadRole` with read
   perms on CloudWatch, X-Ray, and OAM sink).
2. Wire an AMP workspace `prod-prometheus` in source account
   `444455556666` to be queryable from Grafana via a cross-account
   `AMPQueryRole`.

## Known facts

- **Monitoring account:** `111122223333` (us-east-1).
- **Grafana workspace:** `g-abcdef1234` (us-east-1).
- **Grafana role:** `GrafanaCrossAccountReadRole` (already
  created with CloudWatch / X-Ray / OAM read permissions).
- **AMP workspace:** `prod-prometheus` in source account
  `444455556666`.
- **AMP role:** `AMPQueryRole` (to be created in the source
  account, trusting the monitoring account principal).

## Symptom

The operator needs the Grafana data-source wiring CLI and the AMP
cross-account role trust + permission setup, plus verification
that both data sources return cross-account data.
