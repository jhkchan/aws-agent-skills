# Eval prompt: auth-token-expired-ci-cache

Diagnose the ECR push failure for the following repository. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `docker push` returns `denied: Your authorization token has
expired. Reauthenticate at ...` on every push from the CI runner. The
push was working 14 hours ago; failures began 2 hours ago.

```text
Registry: 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: auth-token-expired-ci-cache
Tag: v1
Caller IAM principal: arn:aws:iam::111111111111:user/ci-bot
Push command: docker push
  111111111111.dkr.ecr.us-east-1.amazonaws.com/auth-token-expired-ci-cache:v1
Last successful push: 14 hours ago
CI cache: ~/.docker/config.json is cached across CI jobs and not
  invalidated between runs.

aws ecr get-authorization-token (freshly issued):
  proxyEndpoint: https://111111111111.dkr.ecr.us-east-1.amazonaws.com
  expiresAt: <now + 12 hours>
Cached token in ~/.docker/config.json:
  decoded username: AWS
  decoded password X-amz-expires value: 43200
  issued approximately 14 hours ago

aws iam simulate-principal-policy for ci-bot:
  ecr:GetAuthorizationToken on *: ALLOWED
  ecr:BatchCheckLayerAvailability on repository: ALLOWED
  ecr:PutImage on repository: ALLOWED
  ecr:CompleteLayerUpload on repository: ALLOWED
```

The ECR auth token is base64(`AWS`:`<password>`) and is valid for 12
hours from issue. Docker caches the token in `~/.docker/config.json`
and does not refresh it automatically. A CI runner that caches the
docker config across jobs will hit this deterministically once the
12-hour window elapses.
