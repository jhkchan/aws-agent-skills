# Eval prompt: ec2-passrole-missing

Diagnose the following EC2 `Client.UnauthorizedOperation` incident. Walk
the EC2-specific path (Step 5 of the decision tree). Emit the standard
VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An operator launches an EC2 instance with instance profile
`arn:aws:iam::111111111111:role/ec2-app-profile`. The launch fails.

## Known facts

- Caller identity policy includes:
  - `ec2:RunInstances` on `*`
  - `ec2:Describe*` on `*`
- No `iam:PassRole` permission anywhere in the caller's attached
  policies (managed or inline).
- No SCP, permissions boundary, or session policy on the caller.
- Instance profile role `ec2-app-profile` exists.

## Symptom

```
Client.UnauthorizedOperation: You are not authorized to perform this
operation. Encoded authorization failure message: ...
```

The decoded authorization failure message indicates the request failed
at the `iam:PassRole` check for the instance profile ARN.
