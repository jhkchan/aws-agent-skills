# Baseline (no-skill) — credential-helper-sts-exchange

> This is the response a model produces **without** the skill
> definition. It mentions the signing helper but does not show the
> complete credential-process invocation with all required flags
> (certificate, private-key, trust-anchor-id, profile-id, role-arn),
> does not provide the AWS CLI credential_process profile
> configuration, and does not emit the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

You can use the AWS signing helper to get credentials:

```bash
./aws_signing_helper credential-process \
  --certificate client-cert.pem
```

Point it at your certificate and role and it should work.
