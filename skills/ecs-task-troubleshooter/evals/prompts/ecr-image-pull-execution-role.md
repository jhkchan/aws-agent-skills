# Eval prompt: ecr-image-pull-execution-role

Diagnose the following ECS image-pull failure. Walk the image-pull
diagnostic tree (Step 2 of the decision tree) and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, REASON, EVIDENCE,
REMEDIATION). VERDICT is `ROOT_CAUSE_IDENTIFIED` or `INSUFFICIENT_DATA`.

## Scenario

A Fargate task fails to start with an image-pull error. Cluster
`prod-app`, service `api-svc`.

## Known facts

- `describe-tasks` for the failing task:
  - `stoppedReason: "Essential container in task exited"`
  - `containers[0].reason: "CannotPullContainerError: inspect image
    has been retried 5 times"`
  - `containers[0].exitCode` is absent (container never started)
- `describe-task-definition` shows the image reference:
  `111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1`
- The execution role (`ecsTaskExecutionRole`) has only an inline
  policy granting:
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
  - No ECR actions.
- `aws ecr describe-images --repository-name app --image-ids imageTag=v1`
  returns the image successfully — image exists.
- `aws iam simulate-principal-policy` for the execution role against
  `ecr:BatchGetImage` on `arn:aws:ecr:us-east-1:111111111111:repository/app`
  returns `implicitDeny`.
- Same-account (image and task are both in `111111111111`).
- VPC endpoint for ECR is configured; NAT gateway route exists.

## Symptom

The task transitions from PROVISIONING directly to STOPPED with the
CannotPullContainer error, every time the scheduler retries.
