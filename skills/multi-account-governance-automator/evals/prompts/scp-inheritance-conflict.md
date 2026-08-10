# Eval prompt: scp-inheritance-conflict

Validate this existing SCP inheritance chain. Emit the standard
GOVERNANCE block.

SCP at root (attached to root r-abc0):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowEC2",
    "Effect": "Allow",
    "Action": ["ec2:*"],
    "Resource": "*"
  }]
}
```

SCP at Workloads-Prod OU (attached to ou-prod-123):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyLargeInstances",
    "Effect": "Deny",
    "Action": ["ec2:RunInstances"],
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "ec2:InstanceType": ["m5.24xlarge", "r5.24xlarge"]
      }
    }
  }]
}
```

Operator reports: "prod accounts cannot launch m5.24xlarge even though
the root Allow should override the OU Deny. The Allow at root should
win."

Expected: MANUAL_STEP_REQUIRED. SCP evaluation is intersectional —
Deny always wins over Allow regardless of where in the OU tree each
is attached. The operator's mental model is wrong. The Allow at root
does NOT override the Deny at the child OU. The fix is to add a
condition exception in the Deny SCP or restructure the policy hierarchy.
