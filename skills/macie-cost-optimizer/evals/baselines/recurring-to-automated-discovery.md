# Baseline (no-skill) response: recurring-to-automated-discovery

This file captures what a generic assistant produces WITHOUT the
macie-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, automated-vs-targeted citation,
dollar savings estimate, CONFIRM gate, coverage-verification step).

---

Your Macie setup has a daily recurring job scanning 18 buckets totaling
about 37 TB per month. That's a lot of scanning! Since you have
automated discovery enabled but aren't really using it, you might want
to lean on that more.

The daily targeted job is probably your biggest cost driver at over
$37,000 per month. If you switch to automated discovery, Macie will
only scan new and changed objects instead of the whole data lake every
day.

You can disable the recurring job with:

```
aws macie2 update-classification-job --job-id job-targeted-pci-scan --status DISABLED
```

You should also exclude the log and archive buckets since they don't
contain sensitive data. And your managed identifier selector is set to
ALL, which is overkill if you only need PCI categories.

This should save you a significant amount, though I can't give you an
exact figure without more details on your pricing tier.
