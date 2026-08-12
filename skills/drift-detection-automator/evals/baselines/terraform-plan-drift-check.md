# Baseline (no-skill) response: terraform-plan-drift-check

This file captures what a generic assistant produces WITHOUT the
drift-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Terraform exit-code
logic, GitHub Actions integration, drift report export).

---

For Terraform drift detection, you can run terraform plan in your CI/CD
pipeline on a schedule. If the plan shows changes, that means there's
drift between your Terraform state and the actual infrastructure.

You can set up a GitHub Actions workflow that runs terraform plan daily.
If there are changes, send a notification via SNS.

The terraform plan command has a -detailed-exitcode flag that returns
exit code 2 when there are changes. You can use that to trigger alerts.

Something like:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - run: terraform plan
```

I don't remember the exact flag syntax. You might need to check the
Terraform docs.
