# Eval prompt: instance-not-registered-agent-stopped

Diagnose the SSM Session Manager failure for the following instance.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `i-0abcdef1234567890` does not appear in the SSM Fleet
Manager console. Operators cannot start Session Manager sessions.
The instance is a Linux EC2 instance in a public subnet with route
to IGW.

```text
InstanceId: i-0abcdef1234567890
PlatformName: Amazon Linux
PlatformVersion: 2
InstanceProfile: EC2-SSM-Profile attached, role
  EC2-SSM-Role has AmazonSSMManagedInstanceCore
AgentVersion: 3.2.1546.0
PingStatus: ConnectionLost
LastPingDateTime: 2026-08-09T14:30:00Z (more than 24h ago)
RegistrationDate: 2026-07-15T09:00:00Z

describe-instance-information output: instance is ABSENT
  from the response (no entry for this InstanceId).

VPC: vpc-pub with internet gateway; route table has IGW route.
  Instance has public IP assigned.
SecurityGroup egress: 0.0.0.0/0 on 443 — egress is OPEN.

On-instance probe (via EC2 Serial Console):
  sudo systemctl status amazon-ssm-agent
  → Loaded: loaded (...; disabled; vendor preset: disabled)
  → Active: inactive (dead) since 2026-08-09T14:28Z
  → The agent was stopped by an operator and never restarted.

VPC endpoints in the VPC: none (public subnet, not needed since
  the instance reaches ssm.us-east-1.amazonaws.com via the IGW).
```

The agent is installed and recent enough; the instance role is
correct; the network path is open. Identify the registration-layer
root cause.
