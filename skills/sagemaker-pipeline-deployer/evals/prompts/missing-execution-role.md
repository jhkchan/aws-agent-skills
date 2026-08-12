# Eval: missing-execution-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no execution role provided and default role lacks iam:PassRole for child-job roles

## Prompt

Build a SageMaker Pipeline named training-pipeline in us-east-1
with ProcessingStep, TrainingStep, and RegisterModelStep. I have
not set up an execution role yet — please use the default
SageMaker role and proceed. Pipeline should register to group
classifier-group.
