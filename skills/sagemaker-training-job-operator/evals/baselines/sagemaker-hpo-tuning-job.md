# Baseline (no-skill) response: sagemaker-hpo-tuning-job

This file captures what a generic assistant produces WITHOUT the
sagemaker-training-job-operator skill loaded.

---

To set up hyperparameter tuning in SageMaker, use
`create-hyper-parameter-tuning-job`. You'll need to define the
parameter ranges and the objective metric.

```
aws sagemaker create-hyper-parameter-tuning-job \
  --hyper-parameter-tuning-job-name bert-hpo-2026-08 \
  --hyper-parameter-tuning-job-config '...' \
  --training-job-definition '...'
```

You can also do a warm start from a previous tuning job by adding
`--warm-start-config`. Set `MaxNumberOfTrainingJobs` to 50 and
`MaxParallelTrainingJobs` to 4.
