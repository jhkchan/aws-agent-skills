# Baseline (no-skill) — missing-iam-role

> This is the response a model produces **without** the skill
> definition. It attempts server creation without verifying that the
> IAM role exists, missing the prerequisite entirely. Users would
> authenticate but fail to read/write S3 objects at runtime.
> Generated for with-skill-vs-baseline comparison.

---

Create the SFTP server:

```bash
aws transfer create-server --protocols SFTP
```

Then create the user with their SSH key. The IAM role can be created
later if needed.
