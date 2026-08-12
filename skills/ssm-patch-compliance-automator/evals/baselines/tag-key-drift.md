# Baseline (no-skill) response: tag-key-drift

This file captures what a generic assistant produces WITHOUT the
ssm-patch-compliance-automator skill loaded.

---

It sounds like your patch configuration is set up but the instances
aren't being patched. Let me think about what could be wrong.

The baseline exists and is registered for the patch group, the
maintenance window is configured, and the SSM agent is online. The
fact that describe-instance-patch-states returns 0 instances suggests
the instances aren't being associated with the patch group.

Check that your instances are properly tagged. The tag should match
what the maintenance window is targeting. You have "PatchGroup" as
the tag key and the maintenance window targets "Patch Group" — these
might need to match exactly. Maybe try renaming the tag or updating
the maintenance window target to use "PatchGroup" instead.

Also check that the SSM agent is running the latest version and that
the instances have the correct IAM role attached.
