# Baseline (no-skill) — missing-finding-context

> This is the response a model produces **without** the skill definition.
> It guesses at a remediation path without asking for the finding ARN or
> finding JSON, missing the NEED_MORE_INFO gate that prevents
> misclassification. Generated for with-skill-vs-baseline comparison.

---

Sounds like you have a CVE. Here are the steps:

1. Go to the Inspector console.
2. Find the finding.
3. Patch the instance.

```bash
aws ssm send-command --instance-ids <i-id> \
  --document-name AWS-RunPatchBaseline
```
