# Baseline (no-skill) — batch-inference-s3

> This is the response a model produces **without** the skill
> definition. It writes a Python loop calling GetRecommendations per
> user instead of using the native batch inference job API, missing
> the purpose-built S3-input → S3-output pattern and the IAM role
> requirements. Generated for with-skill-vs-baseline comparison.

---

Write a script that loops over the users and calls GetRecommendations
for each one:

```python
for user_id in user_list:
    recs = personalize_runtime.get_recommendations(
        campaignArn=campaign_arn, userId=user_id, numResults=25
    )
    write_to_s3(recs, f"s3://batch-output/recs/{user_id}.json")
```

That will produce a recommendation file per user.
