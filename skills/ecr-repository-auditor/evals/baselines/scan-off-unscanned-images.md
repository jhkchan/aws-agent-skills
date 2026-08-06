# Baseline (no-skill) response: scan-off-unscanned-images

This file captures what a generic assistant produces WITHOUT the
ecr-repository-auditor skill loaded.

---

This repository has scanOnPush set to false, which means images are not
automatically scanned for vulnerabilities when pushed. You have some
images that haven't been scanned.

You should enable scan-on-push so that images are scanned automatically.
The repository policy looks fine since it's same-account only.
