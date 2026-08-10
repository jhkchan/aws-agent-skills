# Baseline (no-skill) response: arm64-migration-opportunity

This file captures what a generic assistant produces WITHOUT the
lambda-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, ARM64 compatibility verification,
dollar savings math, CONFIRM gate).

---

Your Python Lambda function is running on x86_64 architecture. AWS
Graviton (ARM64) Lambda is about 20% cheaper, so you could save on
compute costs by switching to arm64.

Since you're using Pillow for image processing and Pillow has ARM wheels
available, this should work without code changes.

You can update the architecture with:

```
aws lambda update-function-configuration --function-name fn-arm64-migration-opportunity --architectures arm64
```

Make sure to test it after the change to verify everything works on ARM.
With 20 million invocations per month, the 20% discount should add up to
meaningful savings.
