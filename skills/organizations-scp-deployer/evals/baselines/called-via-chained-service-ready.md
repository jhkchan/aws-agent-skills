# Baseline (no-skill) response: called-via-chained-service-ready

This file captures what a generic assistant produces WITHOUT the
organizations-scp-deployer skill loaded.

---

To allow IAM actions only when called via CloudFormation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:PassRole"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:CalledVia": ["cloudformation.amazonaws.com"]
        }
      }
    }
  ]
}
```

Create and attach to the OU:

```bash
aws organizations create-policy --content file://scp.json \
  --name allow-iam-via-cloudformation --type SERVICE_CONTROL_POLICY
aws organizations attach-policy --policy-id <id> --target-id ou-app-a
```
