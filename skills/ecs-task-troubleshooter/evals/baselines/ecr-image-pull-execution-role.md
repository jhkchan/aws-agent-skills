# Baseline (no-skill) response: ecr-image-pull-execution-role

This file captures what a generic assistant produces WITHOUT the
ecs-task-troubleshooter skill loaded.

---

Your ECS task cannot pull the container image from ECR. The error
"CannotPullContainerError" usually means the execution role does not
have permission to read from ECR.

Attach the `AmazonEC2ContainerRegistryReadOnly` managed policy to your
execution role. This policy includes all the actions needed to pull
images: `ecr:GetAuthorizationToken`,
`ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and
`ecr:BatchGetImage`.

You may also want to verify that the image exists in ECR and that the
network path from your Fargate task to ECR is open (via NAT gateway or
VPC endpoint).
