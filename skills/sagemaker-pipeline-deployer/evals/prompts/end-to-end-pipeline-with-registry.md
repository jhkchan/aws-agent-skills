# Eval: end-to-end-pipeline-with-registry

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ProcessingStep → TrainingStep → ConditionStep → CreateModel/Transform/RegisterModel DAG with property references, PendingManualApproval gate, caching and parallelism

## Prompt

Build a SageMaker Pipeline named xgb-training-pipeline in
us-east-1. Step 1 preprocess raw data with sklearn 1.2-1 on
ml.m5.xlarge (ProcessingStep "Preprocess"). Step 2 train built-in
XGBoost 1.7-1 on ml.m5.2xlarge x2 (TrainingStep "Train") consuming
the Preprocess train/validation outputs via property references.
Step 3 evaluate and ConditionStep "CheckAUC" branches when
accuracy >= 0.9 (ApprovalThreshold parameter). On success run
CreateModelStep, TransformStep (batch input
s3://my-ml-bucket/batch-input), and RegisterModelStep to group
xgb-classifier-group in PendingManualApproval status. Enable
caching with 30-day window. Parallelism MaxParallelExecutionSteps=3.
Execution role arn:aws:iam::123456789012:role/SageMakerPipelineExecutionRole.
