# Baseline (no-skill) response: delegated-admin-multiaccount

This file captures what a generic assistant produces WITHOUT the
inspector2-automation-automator skill loaded.

---

To handle findings across 15 member accounts, designate a delegated
admin for Inspector. Then you can see all findings in one place.

```
aws organizations register-delegated-administrator --account-id 111111111111 --service-principal inspector2.amazonaws.com
```

After that, enable Inspector in each member account from the
delegated admin and the findings will aggregate.
