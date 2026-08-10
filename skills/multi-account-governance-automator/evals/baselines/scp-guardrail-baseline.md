# Baseline (no-skill) response: scp-guardrail-baseline

This file captures what a generic assistant produces WITHOUT the
multi-account-governance-automator skill loaded.

---

To create SCPs for your organization, use the AWS Organizations console
or CLI. You'll want to create policies that deny dangerous actions.

Here's an example SCP that denies leaving the organization:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "organizations:LeaveOrganization",
    "Resource": "*"
  }]
}
```

You can also create SCPs to deny root account actions and prevent
disabling GuardDuty or CloudTrail. Attach these policies to the root so
all member accounts inherit them.

Use the `aws organizations create-policy` and
`aws organizations attach-policy` commands to create and attach SCPs.
Test on a sandbox account first before attaching to the root.
