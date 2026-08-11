# Baseline (no-skill) — missing-execution-role-trust

> This is the response a model produces **without** the skill
> definition. It creates the document without flagging that the
> execution role (MyEC2Role) is an EC2 instance profile that does
> not have ssm.amazonaws.com in its trust policy. The automation
> will fail at execution time with an authorization error. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Sure, create the document:

```bash
aws ssm create-document --name RemediateEC2 \
  --content file://runbook.json --document-type Automation
```

Then execute with:

```bash
aws ssm start-automation-execution --document-name RemediateEC2 \
  --automation-assume-role arn:aws:iam::123456789012:role/MyEC2Role
```

That should work.
