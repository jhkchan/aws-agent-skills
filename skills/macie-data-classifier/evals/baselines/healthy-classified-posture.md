# Baseline (no-skill) — healthy-classified-posture

> This is the response a model produces **without** the skill
> definition. It provides a generic summary of Macie posture but
> misses the ASDD-vs-job-scope coverage gap analysis, the custom
> identifier regex quality scoring, the suppression rule scope
> red-flag check, the multi-account effective coverage calculation,
> and the CLASSIFIED verdict checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Macie looks healthy in this account. It is enabled, ASDD is on,
and there are classification jobs covering sensitive buckets.
Security Hub export is enabled and findings are being generated.
The posture is good overall.

You can verify with:

```bash
aws macie2 get-macie-session --region us-east-1
aws macie2 list-classification-jobs --region us-east-1
```
