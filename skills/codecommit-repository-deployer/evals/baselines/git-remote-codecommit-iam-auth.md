# Baseline (no-skill) — git-remote-codecommit-iam-auth

> This is the response a model produces **without** the skill
> definition. It defaults to static git credentials for all users,
> missing the git-remote-codecommit (GRC) option for SSO/federated
> environments, the session-token based auth model, and the distinction
> between GRC (auto-rotating session tokens) and static credentials
> (manual rotation). Does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the repository and generate git credentials:

```bash
aws codecommit create-repository \
  --repository-name platform-tools

aws iam create-service-specific-credential \
  --user-name developer \
  --service-name codecommit.amazonaws.com
```

Have each developer use the HTTPS URL with the generated credentials.
