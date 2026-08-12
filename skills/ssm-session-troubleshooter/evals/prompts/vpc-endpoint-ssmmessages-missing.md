# Eval prompt: vpc-endpoint-ssmmessages-missing

Diagnose the SSM Session Manager failure for the following instance.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `i-private-1` is Online in the SSM console
(`describe-instance-information` returns `PingStatus: Online`), but
every Session Manager session started from the CLI times out within
10 seconds with "Your session started, but then timed out while
waiting for the instance to start streaming."

```text
InstanceId: i-private-1
PlatformName: Amazon Linux
AgentVersion: 3.2.1546.0 (newer than 3.0.196)
PingStatus: Online
LastPingDateTime: 2026-08-11T20:55:00Z (current)

InstanceProfile role EC2-SSM-Role has:
  - AmazonSSMManagedInstanceCore (attached)
  - Inline policy grants s3:PutObject on the session bucket
simulate-principal-policy on EC2-SSM-Role for
  ssmmessages:OpenDataChannel: Decision: allowed
  ssmmessages:CreateDataChannel: Decision: allowed
  ssm:StartSession: Decision: allowed

VPC: vpc-priv (no internet gateway, no NAT gateway). The instance
  is in a private subnet only.
VPC endpoints configured in vpc-priv:
  - com.amazonaws.us-east-1.ssm (Interface, State: Available)
  - com.amazonaws.us-east-1.ec2messages (Interface, Available)
VPC endpoints MISSING:
  - com.amazonaws.us-east-1.ssmmessages (NOT FOUND in
    describe-vpc-endpoints)

Endpoint security groups: allow 443 inbound from the instance
  subnet CIDR. Egress on the instance SG: 443 to the subnet CIDR.
Private DNS on the existing endpoints: Enabled.

Agent log (on-instance):
  "TimeoutError: failed to open data channel on
  ssmmessages.us-east-1.amazonaws.com after 10s retries"
  "408 RequestTimeout dialing
  ssmmessages.us-east-1.amazonaws.com"

Session document: SSM-SessionManagerRunShell (default,
  DocumentType: Session, SchemaVersion: 1.0).
```

The instance is Online (control channel works) but the session data
channel fails. IAM passes. Identify the missing-network-layer root
cause and the specific endpoint to add.
