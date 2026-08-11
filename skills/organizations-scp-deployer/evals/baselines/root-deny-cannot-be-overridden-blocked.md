# Baseline (no-skill) response: root-deny-cannot-be-overridden-blocked

This file captures what a generic assistant produces WITHOUT the
organizations-scp-deployer skill loaded.

---

You can deny ec2:* at the root and re-allow it on the OU:

Root SCP:
```json
{
  "Effect": "Deny",
  "Action": "ec2:*",
  "Resource": "*"
}
```

OU SCP (ou-prod-a):
```json
{
  "Effect": "Allow",
  "Action": "ec2:*",
  "Resource": "*"
}
```

Attach both policies and the prod OU will have ec2 access while
other accounts do not.
