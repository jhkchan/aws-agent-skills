# Baseline (no-skill) — tag-policy-enforced-for

> This is the response a model produces **without** the skill
> definition. It creates a tag policy JSON but does not call
> out the TAG_POLICIES policy-type enablement prerequisite,
> does not distinguish enforced_for (blocking) vs audit-only,
> and does not emit a READY_TO_DEPLOY verdict. Generated for
> with-skill-vs-baseline comparison.

---

Here's the tag policy:

```bash
aws organizations create-policy \
  --content '{"tags":{"Environment":{"TagKey":{"Value":"Environment"},"EnforcedFor":["ec2:instance","s3:bucket"],"AllowedValues":["dev","staging","production"]},"Owner":{"TagKey":{"Value":"Owner","CaseSensitive":true}}}}' \
  --name mandatory-tag-policy --type TAG_POLICIES

aws organizations attach-policy --policy-id p-xxx --target-id r-xxxx
```

Tags are now enforced.
