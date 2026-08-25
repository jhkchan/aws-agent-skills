# Error Handling (load on demand) — Comprehend Classifier Deployer

Failed-training-job, low-metrics, endpoint-scaling, and VPC-endpoint failure guidance, moved verbatim from SKILL.md.


---

## Error handling (moved from SKILL.md)

### Training job FAILED
- Check CloudWatch Logs (log group: `/aws/comprehend/<classifier-name>`).
- Common causes: training data format error (wrong column count, invalid
  JSON in Augmented Manifest), S3 access denied, KMS access denied.
- Fix the data or IAM policy, then resubmit (creates a new version).

### Low evaluation metrics (F1 < 0.60)
- Insufficient training data per class. Collect more labeled documents.
- Ambiguous or overlapping class definitions. Re-evaluate the label set.
- Class imbalance. Oversample minority classes or collect more data.

### Endpoint not scaling
- Verify auto-scaling target tracking policy is attached.
- Check CloudWatch alarm for ApproximateBacklogSize exists.
- ScaleInCooldown may be too aggressive; increase to avoid flapping.

### VPC endpoint inference fails
- Security group must allow inbound 443 from the calling resource.
- Route table must include the VPC endpoint entry.
- DNS resolution must be enabled on the VPC.
