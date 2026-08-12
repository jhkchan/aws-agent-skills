# Eval: tuning-step-hpo

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — TuningStep with max_jobs=20 max_parallel_jobs=4, best model fed via get_top_model_s3_uri to CreateModel and RegisterModel

## Prompt

Add a TuningStep "Tune" to my SageMaker Pipeline in us-east-1.
Use the existing XGBoost estimator. Objective: maximize
validation:auc. Ranges: max_depth Integer 3-10, eta Continuous
0.05-0.4. max_jobs=20, max_parallel_jobs=4. After tuning, use
get_top_model_s3_uri to feed a CreateModelStep and a
RegisterModelStep to group xgb-classifier-group
(PendingManualApproval). Pipeline execution role
arn:aws:iam::123456789012:role/SageMakerPipelineExecutionRole.
