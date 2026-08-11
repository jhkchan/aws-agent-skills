# Baseline (no-skill) — branch-protection-and-notification

> This is the response a model produces **without** the skill
> definition. It creates notification rules and triggers but misses the
> SNS topic policy requirement (must grant codestar-notifications.amazonaws.com),
> the Lambda resource policy requirement (must grant codecommit.amazonaws.com),
> the distinction between notification rules and legacy triggers, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create a notification rule and a trigger:

```bash
aws codecommit put-repository-triggers \
  --repository-name my-app-repo \
  --trigger-name "lambda-trigger"
```

Add a notification rule pointing to the SNS topic.
