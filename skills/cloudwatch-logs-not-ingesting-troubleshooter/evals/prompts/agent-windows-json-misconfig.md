# Eval prompt: agent-windows-json-misconfig

Diagnose the CloudWatch Logs not-ingesting scenario for the following
Windows EC2 instance. Walk the symptom-driven diagnostic tree and emit
the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).

Symptom: the CloudWatch agent on a Windows EC2 instance is running
but no logs appear in the expected log group. The application at
`C:\logs\app.log` is actively writing.

```text
LogGroup (expected): /ec2/agent-windows-json-misconfig
Source: CloudWatch agent on Windows EC2
Instance: i-agent-windows-json-misconfig (Windows Server 2022)

Agent config (amazon-cloudwatch-agent.json logs section):
  {
    "logs": {
      "logs_collected": {
        "files": {
          "collect_list": [{
            "file_path": "/var/log/app.log",
            "log_group_name": "/ec2/agent-windows-json-misconfig",
            "log_stream_name": "app",
            "timestamp_formats": ["%Y-%m-%d %H:%M:%S"]
          }]
        }
      }
    }
  }
  Note: file_path uses a Linux-style path; the instance is Windows.
  The actual application log is at C:\logs\app.log.

Agent status: running (Windows service shows OK)
Agent IAM role: CloudWatchAgentServerPolicy attached

Application log at C:\logs\app.log (text format):
  2026-08-11 14:23:01 INFO  request received (id=42)
  2026-08-11 14:23:02 INFO  processing (id=42)
  (NOT JSON — plain text lines)

aws logs describe-log-streams:
  logStreams: [] (no streams)
aws logs describe-log-groups:
  logGroups: [] (log group does not exist — agent never wrote)
```

The agent's `file_path` must match the OS-specific path. Windows
instances use `C:\\logs\\app.log`, not `/var/log/app.log`. A
mismatched path silently captures nothing; the agent reports healthy
but ships zero events.
