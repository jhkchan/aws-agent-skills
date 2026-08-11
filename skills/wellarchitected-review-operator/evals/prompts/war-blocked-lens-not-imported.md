# Eval prompt: war-blocked-lens-not-imported

Diagnose why the Prosperity lens cannot be associated with the
workload. Walk the pre-flight checks and emit the standard
VERDICT block with REMEDIATION.

## Scenario

An operator wants to associate the `wellarchitected-prosperity`
lens with workload "checkout-service" (id `workload-abc123`) in
`us-east-1`.

## Known facts

- **Workload id:** `workload-abc123`.
- **Target lens:** `wellarchitected-prosperity`.
- **Lens availability:** `aws wellarchitected list-lenses
  --region us-east-1` does NOT include the Prosperity lens —
  it has NOT been imported.
- **Caller permissions:** `wellarchitected:AssociateLenses`
  only (no `wellarchitected:ImportLens`).
- **Operator intent:** associate the Prosperity lens and
  answer Prosperity questions.

## Symptom

The operator wants to associate the Prosperity lens. Walk the
pre-flight check for lens availability and surface the gap with
the remediation step.
