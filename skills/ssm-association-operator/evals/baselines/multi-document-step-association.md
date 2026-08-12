# Baseline (no-skill) — multi-document-step-association

> This is the response a model produces **without** the skill
> definition. It creates the document but does not explicitly set the
> default version (so the association cannot safely reference it),
> does not pin the association to the document version, and skips the
> OPERATION_COMPLETED checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the document:

```bash
aws ssm create-document \
  --content file://custom-webfleet-provision.yaml \
  --name Custom-WebFleetProvision \
  --document-type Command \
  --document-format YAML \
  --region us-east-1
```

Then create the association:

```bash
aws ssm create-association \
  --name Custom-WebFleetProvision \
  --targets "Key=tag:Role,Values=web" \
  --schedule-expression "cron(0 4 * * MON-FRI *)" \
  --region us-east-1
```
