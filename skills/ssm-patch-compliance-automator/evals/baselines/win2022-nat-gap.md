# Baseline (no-skill) response: win2022-nat-gap

This file captures what a generic assistant produces WITHOUT the
ssm-patch-compliance-automator skill loaded.

---

You can set up SSM Patch Manager for your Windows Server 2022
instances. Create a patch baseline for Windows and configure it to
approve Critical and Important security updates. Then set up a
maintenance window to install them weekly.

```
aws ssm create-patch-baseline --name "win2022-prod-baseline" --operating-system WINDOWS ...
aws ssm create-maintenance-window --name "win-patch-window" --schedule "cron(0 2 ? * SUN *)" ...
```

Tag your instances with the patch group and register them with the
maintenance window. The AWS-RunPatchBaseline document should handle
the installation.

I think Windows instances should be able to download updates from
Windows Update as long as they have internet access through a NAT
gateway or something. You may want to check your VPC configuration
to make sure the instances can reach the update servers.
