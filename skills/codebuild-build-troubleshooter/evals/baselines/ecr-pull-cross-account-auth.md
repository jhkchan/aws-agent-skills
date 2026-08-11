# Baseline (no-skill) response: ecr-pull-cross-account-auth

This file captures what a generic assistant produces WITHOUT the
codebuild-build-troubleshooter skill loaded.

---

Your CodeBuild build is failing because it can't pull the Docker image
from ECR. The error BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE usually means
there's a permissions issue or the image doesn't exist. Check that the
image exists in the ECR repository and that the IAM role has permission
to pull from ECR. You might also want to check if the image is too large
or if there are network issues.

If the image is in a different account, make sure the cross-account
permissions are set up correctly. Try adding ECR permissions to your
CodeBuild service role.
