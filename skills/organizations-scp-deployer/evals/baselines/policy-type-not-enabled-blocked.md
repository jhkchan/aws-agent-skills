# Baseline (no-skill) response: policy-type-not-enabled-blocked

This file captures what a generic assistant produces WITHOUT the
organizations-scp-deployer skill loaded.

---

Here is the SCP to deny root user actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {"aws:PrincipalType": "root"}
      }
    }
  ]
}
```

Create and attach it:

```bash
aws organizations create-policy --content file://scp.json \
  --name deny-root-user-actions --type SERVICE_CONTROL_POLICY
aws organizations attach-policy --policy-id <id> --target-id r-abc1
```
