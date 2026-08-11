# Baseline (no-skill) response: ses-configuration-set-event-publishing-and-ip-pool

This file captures what a generic assistant produces WITHOUT the
ses-email-deployer skill loaded.

---

To create a configuration set, use:

```
aws sesv2 create-configuration-set --configuration-set-name transactional-cs
```

You can add event destinations in the console. For dedicated IPs,
request them from AWS support and then create a pool. Warmup
happens automatically.

```
aws sesv2 create-dedicated-ip-pool --pool-name transactional-pool
```
