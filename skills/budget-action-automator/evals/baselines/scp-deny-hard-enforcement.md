# Baseline (no-skill) response: scp-deny-hard-enforcement

This file captures what a generic assistant produces WITHOUT the
budget-action-automator skill loaded.

---

For hard enforcement, you can attach an SCP via a budget action
when the budget breaches 100%. The SCP denies ec2:RunInstances so
no new instances can launch.

```
aws budgets put-budget-action --action-type APPLY_SCP_FAMILY ...
```

The SCP has to already exist in Organizations. Then the budget
action attaches it when the threshold fires.
