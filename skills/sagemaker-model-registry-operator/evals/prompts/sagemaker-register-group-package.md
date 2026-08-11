# Eval prompt: sagemaker-register-group-package

Register a model package in SageMaker Model Registry. Walk the
pre-flight checks and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
STATE, VERSION, NOTES, CONFIRM).

## Scenario

An operator wants to register a trained XGBoost model
"fraud-detection-2026-08-v1" in `us-east-1` as version 5 of
model package group "fraud-detection-classifier".

## Known facts

- **Group:** "fraud-detection-classifier" exists, status
  `Completed`, latest version is 4.
- **Model artifact:**
  `s3://ml-models/fraud-detection/2026-08/output/model.tar.gz`
  (caller role has `s3:GetObject`).
- **Inference image:**
  `763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1-cpu-py3`
  (exists in ECR).
- **ModelMetrics:** JSON files exist in
  `s3://ml-metrics/fraud-detection/2026-08/` (quality, bias,
  explainability, data-quality).
- **Caller permissions:** `sagemaker:CreateModelPackage`.
- **KMS key** `arn:aws:kms:us-east-1:111122223333:key/abc`
  decryptable.
- **Approval intent:** the operator wants the package to require
  manual approval before production deployment.

## Symptom

The operator needs the exact CLI sequence and the expected
version number.
