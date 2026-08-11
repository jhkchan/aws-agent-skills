# Baseline (no-skill) response: savings-plans-vs-ri-for-graviton-migration

This file captures what a generic assistant produces WITHOUT the
ec2-reserved-capacity-optimizer skill loaded.

---

Since you're planning to migrate from c5 to c7g (Graviton) in 3 months,
you probably shouldn't buy Standard RIs for c5 because you'd be locked
into that instance family. A Savings Plan would be more flexible since
it covers multiple instance types.

You could get a Compute Savings Plan that would give you a discount
while still allowing you to switch to Graviton when you're ready. The
discount won't be as deep as Standard RIs but the flexibility is worth
it in your case.
