# Baseline (no-skill) response: timedout-agent-unreachable

This file captures what a generic assistant produces WITHOUT the
ssm-association-troubleshooter skill loaded — note the absence of
the 3-layer health check, the VPC endpoint gap detection, and the
structured VERDICT that the skill adds.

---

The association is timing out because the SSM Agent cannot reach
the instance. The instance shows PingStatus=ConnectionLost which
means the agent is not checking in. You should restart the SSM
Agent on the instance and verify the network connection.

If the instance is in a private subnet, you may need to check
that it can reach SSM endpoints.
