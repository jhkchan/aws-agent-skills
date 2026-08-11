# Baseline (no-skill) response: express-one-zone-ml-model-serving-latency

---

Your ML cold-start latency is dominated by the 200 MB model-weight
read. Try these steps:

1. Bundle the model weights into the AMI / container image.
2. Use EFS for shared model storage with lower latency.
3. Pre-warm the model cache on instance startup.
4. Consider local instance storage for the model files.

The 80 ms FirstByteLatency is typical for standard S3 in 2026.
