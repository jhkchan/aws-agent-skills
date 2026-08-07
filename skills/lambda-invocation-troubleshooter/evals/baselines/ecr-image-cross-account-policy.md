# Baseline (no-skill) response: ecr-image-cross-account-policy

---

Your Lambda can't pull the container image. The error says "ImagePullFailure"
and the image is reported as "not found". Even though the image exists in
ECR, Lambda can't access it because the function is in account 222222222222
and the ECR repo is in account 111111111111.

Cross-account Lambda container images require extra setup. You need to
make sure the ECR repo policy allows the Lambda service in the other
account to pull the image. Also verify the Lambda execution role has
permission to call ecr:BatchGetImage.
