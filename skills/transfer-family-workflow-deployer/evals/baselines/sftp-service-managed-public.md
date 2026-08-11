# Baseline (no-skill) — sftp-service-managed-public

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the session policy
> requirement for per-user S3 scoping, the IAM role trust policy for
> transfer.amazonaws.com, the LOGICAL home directory mapping semantics,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the SFTP server:

```bash
aws transfer create-server --protocols SFTP
```

Then create users with their SSH keys and an IAM role.
