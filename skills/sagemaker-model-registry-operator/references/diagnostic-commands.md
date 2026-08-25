# Diagnostic Commands — SageMaker Model Registry Operator

Pre-flight and diagnostic command listings moved out of the SKILL.md body. Loaded on demand.


## Pre-flight: model package metadata gate — live-account pre-flight (skip if offline plan)

1. `sagemaker describe-model-package-group --model-package-group-name <group>` — confirm group exists; capture `ModelPackageGroupArn`, `ModelPackageGroupStatus`.
2. `sagemaker list-model-packages --model-package-group-name <group>` — surface existing versions; the next version number is `max(versions) + 1`.
3. `s3api head-object --bucket <bucket> --key <key>/model.tar.gz` — confirm model artifact exists.
4. `ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` — confirm each inference image exists.
5. `s3api head-object` on each `ModelMetrics` S3 URI — confirm metrics files exist.
6. `iam simulate-principal-policy` — confirm caller holds the required `sagemaker:*` and resource-access permissions.
7. `kms describe-key --key-id <id>` — confirm KMS key (if configured) is enabled and the caller can use it.
