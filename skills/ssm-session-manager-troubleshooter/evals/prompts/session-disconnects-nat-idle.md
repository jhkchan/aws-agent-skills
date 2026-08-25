# Eval prompt: session-disconnects-nat-idle

Diagnose the following SSM Session Manager disconnect. Emit the
standard DIAGNOSIS block.

Diagnosis reference: session-disconnects-nat-idle
Account: 111111111111
Region: us-east-1
Instance-id: i-0ccc333eee444fff5
Session-id: jacky-0a1b2c3d4example
Symptom: SessionDisconnects

Recent diagnostic output:
- describe-sessions: SessionId=jacky-0a1b2c3d4example,
  Duration=5m52s, TerminateReason=ConnectionLost
- Pattern: every idle session drops at ~5m50s; active sessions
  (typing commands) stay connected past 20 min.
- describe-instance-information: PingStatus=Active,
  LastPingDateTime within last 2 min.
- SSM-SessionManagerRunShell: idleDisconnectTimeout=1200 (20 min),
  maxSessionDuration=60.
- ec2 describe-route-tables: instance subnet routes 0.0.0.0/0
  via nat-0abc123 (NAT gateway). No ssmmesages VPC endpoint.

Emit the standard DIAGNOSIS block. Identify the root cause via
Step 7 (SessionDisconnects).
