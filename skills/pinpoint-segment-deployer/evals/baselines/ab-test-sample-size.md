# Baseline (no-skill) — ab-test-sample-size

> This is the response a model produces **without** the skill
> definition. It creates the A/B test without checking sample size
> adequacy for the MDE (an underpowered test produces noise, not
> signal), does not verify percentages sum to 100, and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the campaign with additional treatments:

```bash
aws pinpoint create-campaign \
  --application-id app-abc123 \
  --write-campaign-request '{"Name":"subject-line-ab","AdditionalTreatments":[...]}'
```

Split 40/20/20 with a 20% holdout.
