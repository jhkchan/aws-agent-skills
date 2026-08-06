# Baseline (no-skill) response: disabled-mandatory-control

This file captures what a generic assistant produces WITHOUT the
controltower-control-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, mandatory-control reasoning).

---

One of your mandatory controls (AWS-GR_DISABLE_ROOT_ACCESS_KEYS_NO_HSM)
has a FAILED status. The SCP deployment failed with a CloudFormation stack
rollback, and the SCP is not attached to the OU.

You should retry enabling this control. The other mandatory controls are
all in SUCCEEDED state, the Config recorder is enabled, and the execution
role is present.

To fix this, try enabling the control again or check the CloudFormation
stack events for the failure reason.
