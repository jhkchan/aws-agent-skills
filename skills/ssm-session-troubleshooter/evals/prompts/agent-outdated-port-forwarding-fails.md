# Eval prompt: agent-outdated-port-forwarding-fails

Diagnose the SSM Session Manager port forwarding failure. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: port forwarding from a developer's machine to
`i-jumphost-7` returns `NotSupported` on the first attempt.
Interactive Session Manager sessions work fine.

```text
InstanceId: i-jumphost-7
PlatformName: Amazon Linux
AgentVersion: 2.3.1234.0
PingStatus: Online

InstanceProfile role: EC2-SSM-Role with
  AmazonSSMManagedInstanceCore attached. All ssmmessages:*
  permissions present (simulate-principal-policy allowed).

VPC: private subnet, no internet gateway, no NAT gateway.
VPC endpoints configured: ssm, ec2messages, ssmmessages
  (all Available, all with private DNS enabled).
NO S3 VPC endpoint configured (the agent cannot self-update from
  the S3 package bucket).

Port forwarding command issued:
  aws ssm start-session \
    --document-name AWS-StartPortForwardingSession \
    --target i-jumphost-7 \
    --parameters '{"portNumber":["22"]}'

Response:
  "SessionId: botocore-...-portforward"
  "An error occurred (NotSupported) when calling the StartSession
  operation: Port forwarding requires SSM Agent version 3.0.196.0
  or later. Current agent version on the instance is 2.3.1234.0."

Interactive sessions (SSM-SessionManagerRunShell) work fine to the
  same instance.
```

Interactive sessions work; port forwarding returns NotSupported.
Identify the agent-version root cause and the update path.
