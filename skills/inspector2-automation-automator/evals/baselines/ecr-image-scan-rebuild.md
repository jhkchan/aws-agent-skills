# Baseline (no-skill) response: ecr-image-scan-rebuild

This file captures what a generic assistant produces WITHOUT the
inspector2-automation-automator skill loaded.

---

For the ECR finding, rebuild the image with a patched base. Trigger
your CodeBuild pipeline to pull the latest amazonlinux image and
rebuild prod-app:v1.2.4.

```
aws codebuild start-build --project-name container-rebuild-pipeline
```

Make sure scan-on-push is on so the new image gets scanned after
the build.
