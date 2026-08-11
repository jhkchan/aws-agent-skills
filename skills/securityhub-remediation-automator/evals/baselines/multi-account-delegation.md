# Baseline (no-skill) response: multi-account-delegation

This file captures what a generic assistant produces WITHOUT the
securityhub-remediation-automator skill loaded.

---

For multi-account Security Hub, you can designate a delegated
administrator account using the Security Hub console or CLI. Then invite
member accounts and enable standards for them.

```
aws securityhub enable-organization-admin-account --admin-account-id 222222222222
```

After that, enable FSBP for all members. You can set up EventBridge
rules on the delegated admin to process findings from all accounts.

Make sure each member account has the right permissions and that the
standards are enabled in each region you operate in.
