# Baseline (no-skill) response: deploy-agent-onprem-activation-expired-blocked

This file captures what a generic assistant produces WITHOUT the
datasync-task-operator skill loaded.

---

To activate your on-prem DataSync agent, run:

```bash
aws datasync create-agent \
  --activation-key AAAAAAAAAA \
  --agent-name onprem-agent-nfs
```

Make sure the agent VM has outbound HTTPS access to
`datasync.us-east-1.amazonaws.com`. After activation, the agent
should appear in `aws datasync list-agents`.

You can then create a task referencing the agent.
