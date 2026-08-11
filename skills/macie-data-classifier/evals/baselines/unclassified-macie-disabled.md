# Baseline (no-skill) — unclassified-macie-disabled

> This is the response a model produces **without** the skill
> definition. It says Macie is not enabled and recommends enabling
> it, but misses the UNCLASSIFIED verdict format, the structured
> checklist, the coverage gap quantification (80 unmonitored
> buckets), and the verification command set. Generated for
> with-skill-vs-baseline comparison.

---

Macie is not enabled in this account. You should enable it to
start classifying your S3 data:

```bash
aws macie2 enable-macie-session --region us-east-1
```

After enabling, you can create classification jobs to scan your
80 S3 buckets for sensitive data.
