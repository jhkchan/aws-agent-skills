# Baseline (no-skill) response: shell-access-agent-too-old

This file captures what a generic assistant produces WITHOUT the
ssm-session-manager-troubleshooter skill loaded - the contrast
that proves the skill adds structure (4-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The session is starting but the shell isn't working. This is
likely because your SSM Agent is out of date. The agent version
is 2.2.0.0 which is quite old. You should update the SSM Agent
on the instance.

You can do this by running the AWS-UpdateSSMAgent document via
Run Command, or by updating the package directly on the host.
