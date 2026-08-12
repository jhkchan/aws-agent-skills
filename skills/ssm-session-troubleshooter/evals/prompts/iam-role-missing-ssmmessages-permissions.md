# Eval prompt: iam-role-missing-ssmmessages-permissions

Diagnose the SSM Session Manager failure for the following instance.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: Sessions to `i-bastion-1` start (the CLI returns "Starting
session with SessionId: botocore-...") then fail within 2-3 seconds
with "SessionManagerPlugin: DataChannel not received". The instance
is Online.

```text
InstanceId: i-bastion-1
PlatformName: Amazon Linux 2023
AgentVersion: 3.2.1546.0
PingStatus: Online

InstanceProfile role: EC2-Session-Role (CUSTOM, NOT using
  AmazonSSMManagedInstanceCore).
Attached policies on EC2-Session-Role:
  - Inline "ssm-basics":
      {
        "Statement": [
          {"Effect": "Allow",
           "Action": ["ssm:UpdateInstanceInformation",
                      "ssm:StartSession"],
           "Resource": "*"}
        ]
      }
  - NOTE: the inline policy OMITS ssmmessages:* actions entirely.

simulate-principal-policy on EC2-Session-Role for
  ssmmessages:OpenDataChannel: Decision: implicitDeny
  ssmmessages:CreateDataChannel: Decision: implicitDeny
  ssm:UpdateInstanceInformation: Decision: allowed

Agent log (on-instance):
  "ERROR DataChannel: failed to open data channel"
  "AccessDeniedException: User:
    arn:aws:sts::111111111111:assumed-role/EC2-Session-Role/...
    is not authorized to perform: ssmmessages:OpenDataChannel"

VPC: public subnet with IGW; instance reaches
  ssmmessages.us-east-1.amazonaws.com on the public endpoint.
No VPC endpoints configured (not needed — public subnet).

Caller role (the human invoking start-session):
  simulate-principal-policy for ssm:StartSession: allowed.
```

The caller's `ssm:StartSession` is allowed; the instance role
allows `ssm:UpdateInstanceInformation` but NOT the data-channel
actions. Identify the IAM-layer root cause and the specific
permissions to add.
