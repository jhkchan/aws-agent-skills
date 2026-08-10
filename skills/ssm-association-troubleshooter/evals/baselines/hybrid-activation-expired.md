# Baseline (no-skill) response: hybrid-activation-expired

This file captures what a generic assistant produces WITHOUT the
ssm-association-troubleshooter skill loaded — note the absence
of the activation-expiry detection, the hybrid vs EC2 distinction,
and the ESCALATE verdict that the skill adds.

---

The hybrid instance mi-0abc123def456789a is not showing up in SSM.
The instance may be offline or the agent may not be running. You
should check that the SSM Agent is installed and running on the
on-prem host and that it has network connectivity to AWS.

You may also need to re-register the instance with SSM.
