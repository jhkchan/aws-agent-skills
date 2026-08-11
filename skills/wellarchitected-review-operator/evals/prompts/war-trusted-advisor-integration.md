# Eval prompt: war-trusted-advisor-integration

Integrate Trusted Advisor findings as evidence for cost
optimization pillar answers. Walk the pre-flight checks and
emit the standard VERDICT block with CONFIRM gate.

## Scenario

An operator wants to integrate Trusted Advisor findings into
the cost optimization pillar review for workload
"checkout-service" (id `workload-abc123`) in `us-east-1`.

## Known facts

- **Workload id:** `workload-abc123`.
- **Pillar:** `costOptimization`.
- **TA check:** `LowUtilizationEC2Resources` reports three
  underutilized EC2 instances.
- **Operator intent:** surface TA findings as evidence in the
  answer rationale for the right-sizing question, but the
  risk-tier selection MUST be confirmed by the operator (not
  auto-set by TA).
- **Caller permissions:** `wellarchitected:UpdateAnswer` and
  `trustedadvisor:GetCheckResult`.

## Symptom

The operator needs the TA evidence surfaced in the
`update-answer` rationale with the right-sizing question, and
a CONFIRM gate for the risk-tier selection.
