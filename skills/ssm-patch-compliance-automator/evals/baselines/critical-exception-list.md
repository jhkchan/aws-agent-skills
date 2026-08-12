# Baseline (no-skill) response: critical-exception-list

This file captures what a generic assistant produces WITHOUT the
ssm-patch-compliance-automator skill loaded.

---

For your fleet, you can set up SSM Patch Manager for the 197 general
instances and exclude the 3 critical ones. Just don't tag the
critical instances with the same patch group as the rest.

For the general fleet:
- Tag them with the patch group
- Set up a maintenance window with weekly Install
- Use AWS-RunPatchBaseline with Operation: Install

For the 3 critical instances, you could either leave them untagged
(so Patch Manager ignores them) or create a separate patch group
for them that only does scanning.

I'd recommend keeping a list of which instances are excluded and
why, so you don't lose track of them. Maybe a spreadsheet or a
document somewhere that lists the exceptions.

Make sure to review the exceptions periodically to see if they can
be patched normally.
