# Baseline (no-skill) response: fargate-arm64-arch-mismatch

---

The image you're trying to pull is built for arm64 but your Fargate
task is running on x86_64. You need to either build the image for
amd64, or build a multi-arch image using `docker buildx`.

Rebuild with:
```
docker buildx build --platform linux/amd64 -t 111111111111.dkr.ecr.us-east-1.amazonaws.com/fargate-arm64-arch-mismatch:2026.08 --push .
```

Or switch your Fargate task to arm64 (Graviton) if your application
supports it.
