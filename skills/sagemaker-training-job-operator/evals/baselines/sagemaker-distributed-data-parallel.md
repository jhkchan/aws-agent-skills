# Baseline (no-skill) response: sagemaker-distributed-data-parallel

This file captures what a generic assistant produces WITHOUT the
sagemaker-training-job-operator skill loaded.

---

For distributed training on SageMaker, you can use SageMaker's
Distributed Data Parallel library. Set `InstanceCount` to 4 and
enable the data parallel library in your hyperparameters.

```
aws sagemaker create-training-job \
  --training-job-name bert-pretrain \
  --resource-config '{"InstanceType":"ml.p5.48xlarge","InstanceCount":4}' \
  --hyper-parameters '{"sagemaker_distributed_dataparallel_enabled":true}'
```

Make sure your training script uses the SMDDP library. You should
also enable Training Compiler for better performance on transformers.
