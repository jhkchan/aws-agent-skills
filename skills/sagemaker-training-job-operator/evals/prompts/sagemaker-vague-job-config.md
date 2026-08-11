# Eval prompt: sagemaker-vague-job-config

Plan the launch of a SageMaker training job. Walk the pre-flight
checks and emit the standard VERDICT block (OPERATION, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, MODEL_ARTIFACT, LOG_GROUP,
CONFIRM).

## Scenario

A user reports: "I want to train a model on SageMaker." They
mention it is for "a transformer model" but do not provide further
details.

## Known facts

- No algorithm spec or ECR image provided.
- No input data S3 location provided.
- No output S3 location provided.
- No instance type provided.
- No execution role ARN provided.
- No hyperparameters provided.
- The user has not specified whether the job uses spot training,
  distributed training, warm pools, or HPO.

## Symptom

The user wants to know how to launch the training job.
