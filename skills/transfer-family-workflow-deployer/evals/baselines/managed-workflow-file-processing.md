# Baseline (no-skill) — managed-workflow-file-processing

> This is the response a model produces **without** the skill
> definition. It mentions workflows but misses the on-exception step
> requirement, the workflow-to-server attachment step, the Step
> Functions execution detail, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create a workflow with some steps:

```bash
aws transfer create-workflow --steps file://steps.json
```

Then attach it to your server.
