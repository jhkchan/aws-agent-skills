# Worked Examples — ssm-session-manager-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example - NEED_MORE_INFO, SessionDisconnects (intermittent)

```text
DIAGNOSIS: intermittent-drop-prod
INSTANCE: i-0fedcba9876543210
SESSION: jacky-0a1b2c3d4example
SYMPTOM: SessionDisconnects
ROOT_CAUSE: Pending diagnosis - session drops at irregular
            intervals (not aligned to IdleDisconnectTimeout or
            NAT 350s). Agent and connectivity layers pass. Need
            session-manager-plugin client log and a long-running
            test session to correlate.
EVIDENCE:
  - describe-sessions: SessionId=jacky-0a1b2c3d4example, Duration=4m12s, TerminateReason=ConnectionLost
  - describe-instance-information: PingStatus=Active, LastPingDateTime within last 2 min
  - IdleDisconnectTimeout=20m (not the cause - drop at 4m12s)
LAYER_CHECK:
  - Client: PASS - session-manager-plugin 1.2.612.0
  - IAM: PASS - ssm:StartSession allowed
  - Connectivity: PASS - ssmmesages endpoint present, SG 443 open
  - Agent: PASS - AgentVersion 3.3.131.0, IsLatestVersion true
FIX: (pending root cause)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Capture the session-manager-plugin log from the client
  during the next drop event:
    tail -f ~/.ssm/logs/sessionmanagerplugin.log
  Concurrently, on the instance (via another working session):
    tail -f /var/log/amazon/ssm/amazon-ssm-agent.log | grep -i mgs
  Correlate timestamps to identify whether the drop is client,
  network, or agent side. If the drop aligns with a CloudWatch
  NetworkOut dip, route to VPC connectivity.
ESCALATION_PATH: If correlation points to an SSM-side issue, escalate
  to AWS Support with the session-id and the correlated logs.
```

### Worked example - ESCALATE, cross-account KMS key policy

```text
DIAGNOSIS: cross-acct-session-kms
INSTANCE: i-0bbb222ddd333eee4 (in account 222222222222)
SESSION: none - not started
SYMPTOM: LatestFeature (cross-account)
ROOT_CAUSE: KMS key arn:aws:kms:us-east-1:222222222222:key/abc123
            in the target account does not grant the source-account
            caller kms:GenerateDataKey. The key policy allows only
            the target account root. Cross-account Session Manager
            requires the key policy to grant the source-account
            principal.
EVIDENCE:
  - aws ssm start-session from source account 111111111111 returned: AccessDeniedException ... kms:GenerateDataKey
  - aws kms get-key-policy shows Statement Principal = {"AWS":"arn:aws:iam::222222222222:root"} only
LAYER_CHECK:
  - Client: PASS - session-manager-plugin 1.2.612.0
  - IAM: PASS - source-account caller has ssm:StartSession via the cross-account role
  - Connectivity: PASS - ssmmesages endpoint present in target VPC
  - Agent: PASS - AgentVersion 3.3.131.0
FIX: Cannot remediate from the source account alone - the KMS key
  policy must be modified in the target account. Requires
  target-account key admin access.
VERIFICATION: After key policy update:
  aws kms describe-key --key-id arn:aws:kms:us-east-1:222222222222:key/abc123 --query 'KeyMetadata.KeyState' --output text --profile target-account-admin
  Expect: Enabled. Then re-run start-session from the source account.
VERDICT: ESCALATE
NEXT_STEP: Provide the target-account key admin with this statement
  to add to the key policy:
  {
    "Sid": "AllowSourceAccountSessionManager",
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
    "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
    "Resource": "*"
  }
ESCALATION_PATH: Target-account KMS key administrator must update the
  key policy on arn:aws:kms:us-east-1:222222222222:key/abc123. This
  cannot be done from the source account.
```
