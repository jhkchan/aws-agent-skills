# Baseline (no-skill) response: convertible-ri-exchange-opportunity

This file captures what a generic assistant produces WITHOUT the
ec2-reserved-capacity-optimizer skill loaded.

---

Your Convertible RIs for m5.large are underutilized at 60% because you
right-sized the fleet to m5.xlarge. Since these are Convertible RIs,
you should be able to exchange them for m5.xlarge RIs instead. This
would bring your utilization back up.

You can do the exchange through the AWS Console or CLI. The exchange
doesn't cost anything extra if the new instance type is equal or
greater value.
