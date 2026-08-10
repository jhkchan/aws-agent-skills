# Eval prompt: timedout-agent-unreachable

Diagnose the following SSM association timeout. Emit the standard
DIAGNOSIS block including the 3-layer SSM health check.

Diagnosis reference: timedout-agent-unreachable
Account: 111111111111
Region: us-east-1
Association-id: 1234567890abcdef1234567890abcdef1234567890abcdef1
Instance-id: i-0fedcba9876543210
Symptom: TimedOut

Recent diagnostic output:
- describe-association-executions Status=TimedOut
- describe-instance-information: PingStatus=ConnectionLost,
  LastPingDateTime=2026-08-09T22:00:00Z (12+ hours stale),
  AgentVersion=3.2.1555.0
- ec2 describe-instances: State=running,
  VpcId=vpc-privatesubnet-0abc, IamInstanceProfile has
  AmazonSSMManagedInstanceCore attached
- ec2 describe-vpc-endpoints for vpc-privatesubnet-0abc: returns
  only com.amazonaws.us-east-1.ssm; missing ssmmessages and
  ec2messages endpoints.

Emit the standard DIAGNOSIS block. Identify the root cause via
the 3-layer health check (Step 1).
