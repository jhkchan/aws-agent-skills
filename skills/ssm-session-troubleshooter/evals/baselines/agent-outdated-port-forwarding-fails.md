# Baseline (no-skill) response: agent-outdated-port-forwarding-fails

---

Port forwarding is returning `NotSupported`. The error message says
the agent version is too old — port forwarding needs a newer agent.
You should update the SSM Agent on the instance.

On Amazon Linux, you can run `sudo yum update amazon-ssm-agent` to
get the latest version. After updating, restart the agent and try
the port forwarding command again.
