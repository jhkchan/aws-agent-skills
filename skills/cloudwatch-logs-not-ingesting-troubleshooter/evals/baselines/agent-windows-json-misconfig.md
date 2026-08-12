# Baseline (no-skill) response: agent-windows-json-misconfig

---

Your CloudWatch agent isn't shipping logs. Check the agent
configuration file and make sure the `file_path` points to the actual
log file. On Windows, paths use backslashes like `C:\logs\app.log`.

Also verify the agent service is running and that the IAM role has the
`CloudWatchAgentServerPolicy` attached. Restart the agent after
fixing the config:

```
amazon-cloudwatch-agent-ctl -a stop
amazon-cloudwatch-agent-ctl -a start
```
