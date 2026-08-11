# Eval prompt: war-answer-security-pillar-high-risk

Answer the security pillar questions with a HIGH risk-tier
rationale. Walk the pre-flight checks and emit the standard
VERDICT block.

## Scenario

An operator wants to answer the security pillar questions for
workload "checkout-service" (id `workload-abc123`, lens
`wellarchitected`, pillar `security`).

## Known facts

- **Workload id:** `workload-abc123`.
- **Lens:** `wellarchitected` is associated.
- **Pillar:** `security`.
- **Workload evidence:** the workload has NO automated rollback;
  deployments rely on manual canary watch per the APP-SVC
  rollback SOP.
- **Risk-tier intent:** the risky choice (no automated rollback)
  should be marked `HIGH_ISSUE` with rationale tied to the
  deployment SOP.
- **Caller permissions:** `wellarchitected:UpdateAnswer`.

## Symptom

The operator needs the `update-answer` CLI with the
`ChoiceUpdates` map marking the risky choice `HIGH_ISSUE` and
the rationale tied to the deployment SOP.
