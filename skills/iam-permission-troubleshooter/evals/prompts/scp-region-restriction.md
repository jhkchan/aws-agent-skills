# Eval prompt: scp-region-restriction

Diagnose the following region-based AccessDenied incident. The
CloudTrail event explicitly names an SCP. Walk the Organisation SCP
layer first, then confirm against identity-based policy. Emit the
standard VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A workload deployed to `ap-southeast-2` fails to launch EC2 instances.
The same Infrastructure-as-Code template works in `us-east-1`.

## Known facts

- EC2 instance role identity policy includes:
  - `ec2:RunInstances` on `*`
  - `iam:PassRole` on the instance profile ARN
  - `ec2:Describe*` on `*`
- No permissions boundary on the instance role.
- The production OU root has an SCP with:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Deny",
        "Action": "*",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "aws:RequestedRegion": ["us-east-1", "us-west-2"]
          }
        }
      }
    ]
  }
  ```

## Symptom (from CloudTrail)

```
errorMessage: "User: arn:aws:sts::111111111111:assumed-role/...
is not authorized to perform: ec2:RunInstances ... with an explicit
deny in a Service Control Policy"
```
