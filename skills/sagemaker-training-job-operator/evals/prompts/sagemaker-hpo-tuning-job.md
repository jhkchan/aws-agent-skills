# Eval prompt: sagemaker-hpo-tuning-job

Plan the launch of a SageMaker hyperparameter tuning (HPO) job with
warm start and early stopping. Walk the pre-flight checks and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, MODEL_ARTIFACT, LOG_GROUP, CONFIRM).

## Scenario

An operator wants to launch an HPO job `bert-hpo-2026-08` in
`us-east-1` to tune a BERT classifier.

## Known facts

- **Objective:** maximize `validation:accuracy` (regex
  `val_acc: ([0-9\.]+)`).
- **Tunable parameters:**
  - `learning_rate`: 0.0001 to 0.1, `Logarithmic` scaling
  - `batch_size`: 32 to 256, `Auto` integer scaling
- **Strategy:** Bayesian.
- **Resource limits:** 50 training jobs max, 4 in parallel.
- **Early stopping:** automatic.
- **Base training definition:** `ml.p4de.24xlarge`, 1 instance,
  1024 GB volume; PyTorch GPU image; execution role has all
  required permissions; Service Quota for `ml.p4de.24xlarge` is 8
  (sufficient for 4 parallel jobs).
- **Warm start:** from previous tuning job `bert-hpo-2026-07`,
  same dataset and algorithm (`IdenticalDataAndAlgorithm`).

## Symptom

The operator wants the exact `create-hyper-parameter-tuning-job`
CLI sequence with the warm-start config and early stopping enabled.
