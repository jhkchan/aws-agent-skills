# Baseline (no-skill) response: guardrail-deny-regions-ready

This file captures what a generic assistant produces WITHOUT the
organizations-scp-deployer skill loaded.

---

To deny unapproved regions, create an SCP like this:

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
          "aws:RequestedRegion": ["us-east-1", "eu-west-1", "us-west-2"]
        }
      }
    }
  ]
}
```

Then attach it to the root:

```bash
aws organizations create-policy --content file://scp.json \
  --name deny-unapproved-regions --type SERVICE_CONTROL_POLICY
aws organizations attach-policy --policy-id <id> --target-id r-abc1
```
