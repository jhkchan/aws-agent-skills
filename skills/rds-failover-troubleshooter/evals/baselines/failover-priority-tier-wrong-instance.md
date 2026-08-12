# Baseline (no-skill) response: failover-priority-tier-wrong-instance

---

The wrong instance was promoted during failover. Aurora chooses the
new writer based on the failover priority tier. Check the PromotionTier
setting on each instance.

If you want instance-reader-large to be promoted first, you may need
to set its PromotionTier to 0 and change instance-reader-small to a
higher tier.
