# Eval prompt: cross-account-repo-policy-missing

Diagnose the ECR pull failure for the following cross-account scenario.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ECS task in account `222222222222` fails to start with
`CannotPullContainerError`. The task definition references an image in
account `111111111111`. The image exists; the caller's IAM policy
allows the action; yet the pull is denied.

```text
Registry (image source): 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: cross-account-repo-policy-missing
Tag: 1.0
Image source account: 111111111111
Caller (ECS task execution role) account: 222222222222
Caller IAM role: arn:aws:iam::222222222222:role/ecs-task-exec

aws iam simulate-principal-policy for ecs-task-exec:
  ecr:BatchGetImage on arn:aws:ecr:us-east-1:111111111111:repository/cross-account-repo-policy-missing: ALLOWED
  ecr:GetDownloadUrlForLayer on same repository: ALLOWED
  ecr:GetAuthorizationToken on *: ALLOWED

aws ecr get-repository-policy:
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "SameAccountOnly",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    }]
  }
  Note: Principal lists only account 111111111111. Account 222222222222
  is NOT in any statement.

aws ecr describe-images:
  Tag 1.0 exists, size 450 MB compressed, pushed 2 hours ago.
```

For cross-account ECR access, BOTH the caller's IAM identity-based
policy AND the target repository's resource-based policy must allow
the action. Same-account access needs only IAM; cross-account needs
both. The repository policy here lists only the source account.
