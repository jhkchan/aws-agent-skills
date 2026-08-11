# Baseline (no-skill) — custom-labels-lifecycle

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the hourly inference cost
> warning (model must be stopped when not in use), the start-project-version
> requirement after training, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create a project:

```bash
aws rekognition create-project --project-name industrial-defects
```

Train the model:

```bash
aws rekognition create-project-version \
  --project-arn "..." --version-name "v1"
```
