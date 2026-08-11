# Baseline (no-skill) response: underutilized-ri-after-migration

This file captures what a generic assistant produces WITHOUT the
ec2-reserved-capacity-optimizer skill loaded.

---

It looks like you migrated from c5 to c6i but your Reserved Instances
are still for c5.xlarge. Your utilization dropped to 55% which means
you're paying for RIs that aren't being fully used. Since these are
Standard RIs, you can't exchange them for a different type.

You might want to look into selling them on the RI Marketplace. You
should also consider buying RIs for the new c6i instances that are now
running on-demand.
