# Baseline (no-skill) — nested-stack-validation

> This is the response a model produces **without** the skill
> definition. It lints only the parent template and misses the
> critical requirement that each child template must be linted
> independently (parent-level cfn-lint does NOT recurse into nested
> stacks), does not validate child templates separately, and lacks
> the OPERATION_COMPLETED checklist format. Generated for with-
> skill-vs-baseline comparison.

---

To validate your template:

```bash
cfn-lint parent-template.yaml
aws cloudformation validate-template --template-body file://parent-template.yaml
```

If clean, go ahead and update.
