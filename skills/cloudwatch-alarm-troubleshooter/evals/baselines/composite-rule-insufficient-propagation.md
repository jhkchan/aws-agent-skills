# Baseline (no-skill) response: composite-rule-insufficient-propagation

---

Your composite alarm isn't firing even though one child is in ALARM.
The rule uses AND, which means both children need to be in ALARM for
the composite to fire. Check the HighLatency child — it's in
INSUFFICIENT_DATA, which might be treated as not-ALARM.

If you want the composite to fire when either child is in ALARM, you
might need to change the rule. Also look into why the HighLatency
alarm is in INSUFFICIENT_DATA — there might be a metric emission
problem.
