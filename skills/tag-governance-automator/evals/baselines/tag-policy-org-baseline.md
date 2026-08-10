# Baseline (no-skill) response: tag-policy-org-baseline

This file captures what a generic assistant produces WITHOUT the
tag-governance-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, TagPolicy JSON
template, enforced_for awareness, cascade semantics).

---

You can use AWS Organizations tag policies to enforce required tags.
First enable tag policies on the organization, then create a policy
with your tag keys and allowed values, and attach it to the root.

The tag policy JSON would look something like:

```json
{
  "tags": {
    "Environment": {"allowed_values": ["dev", "staging", "prod"]}
  }
}
```

You'd also want Owner, Project, and CostCenter in there. Attach it
to the root so it applies to all accounts.

I think the CLI command is something like:

```
aws organizations create-policy --type TAG_POLICY ...
```

You might need to look up the exact syntax in the AWS docs.
