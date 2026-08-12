# Baseline (no-skill) — missing-interactions-schema

> This is the response a model produces **without** the skill
> definition. It proceeds to create a solution with the Users dataset
> alone, not realizing that Interactions is the REQUIRED minimum
> dataset. The training job fails at runtime with
> ResourceNotFoundException or InvalidInputException. Generated for
> with-skill-vs-baseline comparison.

---

Create a Users dataset and train a solution:

```bash
aws personalize create-dataset \
  --dataset-group-arn <arn> \
  --dataset-type USERS \
  --schema-arn <users-schema-arn>

aws personalize create-solution \
  --dataset-group-arn <arn> \
  --recipe-arn arn:aws:personalize:::recipe/aws-user-personalization
```

Then create the campaign once the solution version is active.
