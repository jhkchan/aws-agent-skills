# Baseline (no-skill) — nested-runbook-branch-targets

> This is the response a model produces **without** the skill
> definition. It attempts the document but misses the aws:branch
> schema 0.3 requirement, does not properly configure
> aws:executeAutomation for nested runbooks, and omits the tag-based
> target collection pattern. Does not emit a READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

Create a runbook with conditional steps:

```yaml
mainSteps:
  - name: Check
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeInstances
  - name: Branch
    action: aws:branch
    inputs:
      Choices: [...]
```

Then create the child runbook and link them.
