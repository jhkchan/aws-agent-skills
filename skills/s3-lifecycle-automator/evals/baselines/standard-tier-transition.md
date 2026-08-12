# Baseline (no-skill) response: standard-tier-transition

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-automator skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, validation, versioning rules,
expert S3 lifecycle knowledge).

---

You can create a lifecycle policy for your bucket using the S3 console
or CLI. Set up transitions to move objects from Standard to IA after 30
days, then to Glacier after 90 days, and Deep Archive after a year.

```
aws s3api put-bucket-lifecycle-configuration --bucket app-access-logs --lifecycle-configuration ...
```

You'll need to include the transitions in the JSON configuration. Make
sure versioning is enabled if you want to manage non-current versions.

I don't remember the exact JSON format for the lifecycle rules. Check
the S3 documentation for the structure.
