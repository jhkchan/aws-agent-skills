# Eval prompt: shell-access-agent-too-old

Diagnose the following SSM Session Manager shell access failure.
Emit the standard DIAGNOSIS block.

Diagnosis reference: shell-access-agent-too-old
Account: 111111111111
Region: us-east-1
Instance-id: i-0bbb222ddd333eee4
Symptom: ShellAccessFails

Recent diagnostic output:
- aws ssm start-session opens but returns "This shell is not
  configured" and disconnects within 2 seconds.
- describe-instance-information: PingStatus=Active,
  AgentVersion=2.2.0.0, IsLatestVersion=false,
  PlatformType=Linux
- send-command AWS-RunShellScript "ls /bin/bash": present;
  /etc/passwd for ssm-user shows /bin/bash.
- ssm-sessionmanager-console-perm attached to caller; IAM and
  connectivity layers PASS.

Emit the standard DIAGNOSIS block. Identify the root cause via
the 4-layer health check (Step 1, Layer 4).
