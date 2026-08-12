# Baseline (no-skill) response: al2023-prod-auto-install

This file captures what a generic assistant produces WITHOUT the
ssm-patch-compliance-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, baseline template,
maintenance-window concurrency, safety gates, expert Patch Manager
knowledge).

---

You can use AWS Systems Manager Patch Manager to patch your Amazon
Linux 2023 instances. Create a patch baseline with the right approval
rules, tag your instances with a patch group, and set up a maintenance
window to install patches on a schedule.

Here's roughly how to do it:

```
aws ssm create-patch-baseline --name "al2023-prod-baseline" --operating-system AMAZON_LINUX_2023 ...
```

For the maintenance window:

```
aws ssm create-maintenance-window --name "patch-window" --schedule "cron(0 2 ? * SAT *)" ...
```

Then register your instances as targets and add an AWS-RunPatchBaseline
task. Set the operation to Install and it should patch them.

Make sure your instances have the right tags so they're picked up by
the maintenance window. I think the tag key might be something like
"PatchGroup" or "patch group" — you should check the AWS docs to be
sure.

You might also want to set up an SNS notification so you know when
patching is done.
