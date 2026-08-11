# Baseline (no-skill) — team-sharing-write

> This is the response a model produces **without** the skill
> definition. It creates the environment but does not set up team
> sharing, explain the permissions model (each user connects with
> own credentials), or note the read-write vs read-only distinction.
> Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the environment:

```bash
aws cloud9 create-environment-ec2 \
  --name "team-shared-ide" \
  --instance-type t3.medium
```

You can share it with your team from the console.
