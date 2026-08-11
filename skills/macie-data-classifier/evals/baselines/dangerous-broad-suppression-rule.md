# Baseline (no-skill) — dangerous-broad-suppression-rule

> This is the response a model produces **without** the skill
> definition. It mentions the suppression rule but does not flag it
> as a red flag masking High severity findings, does not explain the
> SUPPRESS vs ARCHIVE action difference, does not note that
> suppressed findings never reach Security Hub or CloudWatch Events,
> and misses the PARTIALLY_CLASSIFIED verdict format. Generated for
> with-skill-vs-baseline comparison.

---

Macie appears to be running well with classification jobs covering
20 buckets. There is a suppression rule that filters some findings.
Security Hub shows zero findings which might mean Macie is working
well or it could be because of the suppression rule. You may want
to review the suppression rule criteria.

```bash
aws macie2 list-findings-filters --region us-east-1
```
