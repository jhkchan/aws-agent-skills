# Eval prompt: port-forward-local-port-in-use

Diagnose the following SSM Session Manager port forwarding failure.
Emit the standard DIAGNOSIS block.

Diagnosis reference: port-forward-local-port-in-use
Account: 111111111111
Region: us-east-1
Instance-id: i-0fedcba9876543210
Symptom: PortForwardingFails

Command run:
  aws ssm start-session --target i-0fedcba9876543210 \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["22"],"localPortNumber":["2222"]}'

Recent diagnostic output:
- session-manager-plugin log: "bind: address already in use"
  at session start; session terminated immediately.
- lsof -i :2222: returns PID 4517 (sshd listening on 2222).
- simulate-principal-policy: ssm:StartSession allowed on both
  the instance and AWS-StartPortForwardingSession document.
- describe-instance-information: PingStatus=Active,
  AgentVersion=3.3.131.0.

Emit the standard DIAGNOSIS block.
