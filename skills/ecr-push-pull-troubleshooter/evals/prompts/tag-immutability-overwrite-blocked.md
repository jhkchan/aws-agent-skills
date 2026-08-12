# Eval prompt: tag-immutability-overwrite-blocked

Diagnose the ECR push failure for the following repository. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: CI pipeline push fails with `denied: ... image tag already
exists and is immutable`. The first build (which created the `latest`
tag) succeeded; every subsequent build fails because the pipeline
re-pushes `latest` on every commit.

```text
Registry: 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: tag-immutability-overwrite-blocked
Tag: latest (overwrite attempt)

aws ecr describe-repositories:
  imageTagMutability: IMMUTABLE
  createdAt: 2026-06-01
  encryptionConfiguration.encryptionType: AES256

aws ecr describe-images:
  Tag latest exists, pushed 3 days ago, digest sha256:xyz789

aws ecr get-repository-policy: (none — same-account IAM only)
aws iam simulate-principal-policy for the CI role:
  ecr:PutImage on the repository: ALLOWED
  ecr:GetAuthorizationToken: ALLOWED

Auth token freshly issued (expires in +12 hours).
```

Tag immutability is per-repository, not per-registry. `IMMUTABLE`
blocks tag overwrites on the named repository only. A first-push of
any tag always succeeds; a subsequent push of an existing tag fails.
Switching the repository to `MUTABLE` takes effect immediately but
lets tags float, defeating reproducibility.
