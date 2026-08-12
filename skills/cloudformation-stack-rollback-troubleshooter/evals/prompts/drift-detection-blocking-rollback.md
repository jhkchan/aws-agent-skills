# Eval prompt: drift-detection-blocking-rollback

Diagnose the CloudFormation stack rollback failure for the following
stack. Walk the rollback-focused diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-app` is stuck in `UPDATE_ROLLBACK_FAILED`. The rollback
failed on a Security Group resource because its actual state doesn't
match the expected template state. An operator manually added an ingress
rule via the AWS Console last week (drift).

```text
StackName: prod-app
StackStatus: UPDATE_ROLLBACK_FAILED

Failed resource:
  LogicalResourceId: AppSecurityGroup
  ResourceType: AWS::EC2::SecurityGroup
  ResourceStatus: UPDATE_FAILED
  ResourceStatusReason: "Resource not in expected state:
    Security Group sg-abc123 has ingress rules that do not
    match the template."

Drift detection result:
  StackResourceDriftStatus: MODIFIED
  PropertyDifferences:
    - PropertyPath: /SecurityGroupIngress/1
      DifferenceType: ADD
      ExpectedValue: (not present in template)
      ActualValue: {IpProtocol: tcp, FromPort: 5432,
        ToPort: 5432, CidrIp: 10.0.1.0/24}
    - PropertyPath: /Tags/0/Value
      DifferenceType: NOT_EQUAL
      ExpectedValue: "prod-app-sg"
      ActualValue: "prod-app-sg-manual-edit"

Stack policy: (none)
Nested stacks: (none)
Custom resources: (none)
```

The update that triggered the rollback added a new egress rule. The
rollback tried to remove it, but CloudFormation also tried to reconcile
the manually-added ingress rule and failed because the drifted state
didn't match any expected configuration. Identify the layer and
recommend the fix.
