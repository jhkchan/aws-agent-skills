# Baseline (no-skill) — domain-ecommerce-recommender

> This is the response a model produces **without** the skill
> definition. It creates a CUSTOM dataset group and a full
> solution → solution version → campaign flow, missing that
> ECOMMERCE DOMAIN groups use pre-built recommenders (no solution
> needed). Also misses the minRecommendationRequestsPerSecond cost
> floor. Generated for with-skill-vs-baseline comparison.

---

Create a CUSTOM dataset group and a User-Personalization solution:

```bash
aws personalize create-dataset-group --name shop-recs
aws personalize create-solution \
  --dataset-group-arn <arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization
```

Then create a campaign. That gives you an e-commerce recommendation
endpoint.
