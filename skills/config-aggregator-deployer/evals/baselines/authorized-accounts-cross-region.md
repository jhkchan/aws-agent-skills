# Baseline (no-skill) — authorized-accounts-cross-region

> This is the response a model produces **without** the skill definition.
> It produces a put-configuration-aggregator with account IDs but misses
> the PutAggregationAuthorization requirement on each source account
> (without which source status shows FAILED), the recorder verification
> prerequisite on source accounts, the delivery channel check, and the
> structured checklist output format.

---

Create your Config aggregator with the account IDs:

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name authorized-accounts-aggregator \
  --account-aggregation-sources AccountIds=111111111111,222222222222,333333333333,AllAwsRegions=true \
  --region us-east-1
```

You should see data from those accounts once the aggregator is
created.
