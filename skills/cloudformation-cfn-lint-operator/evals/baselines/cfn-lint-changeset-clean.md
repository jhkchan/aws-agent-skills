# Baseline (no-skill) — cfn-lint-changeset-clean

> This is the response a model produces **without** the skill
> definition. It runs only validate-template (missing the four-layer
> pipeline), does not run cfn-nag for security scanning, does not
> create a ChangeSet for resource change preview, does not mention
> the defense-in-depth approach, and lacks the OPERATION_COMPLETED
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To validate your template:

```bash
aws cloudformation validate-template --template-body file://template.yaml
```

If that passes, go ahead and update the stack.
