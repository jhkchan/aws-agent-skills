# Advanced Patterns (load on demand) — Comprehend Classifier Deployer

2023-2026 Comprehend feature changes, moved verbatim from SKILL.md.


---

## Step 10 — Recent features (2023-2026) (moved from SKILL.md)

**Recent features (2023-2026):**

- **Native PDF classification (2023-2024):** Comprehend supports
  classifying multi-page PDF documents natively using layout and visual
  features in addition to text. Training data as S3 URIs in Augmented
  Manifest format.
- **Auto-scaling for endpoints (2023-2024):** Application Auto Scaling
  supports Comprehend endpoints via ApproximateBacklogSize metric.
- **VPC training support (2024-2025):** Training jobs can run entirely
  within a VPC via VpcConfig in create-document-classifier.
- **Volume KMS encryption (2024-2025):** `--volume-kms-key-id`
  parameter encrypts the EBS volume during training.
- **Multi-label threshold tuning (2025-2026):** Multi-label output
  includes per-class confidence scores that can be independently
  thresholded at inference time without retraining.
- **Terraform provider maturity (2024-2025):** Terraform
  `aws_comprehend_document_classifier` and `aws_comprehend_endpoint`
  now support multi-label, Native PDF, VPC config, and both KMS params.
