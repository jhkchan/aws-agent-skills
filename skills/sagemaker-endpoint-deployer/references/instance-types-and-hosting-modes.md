# Instance Types and Hosting Modes — SageMaker Endpoint Deployer

Reference for selecting the correct SageMaker instance type, hosting mode,
and auto-scaling configuration based on workload characteristics.

## Hosting mode decision matrix

| Mode | Latency | Payload size | Scale-to-zero | Auto-scaling metric | Use when |
|---|---|---|---|---|---|
| **Real-time** | Low (<1s) | < 6 MB | No | InvocationsPerInstance | Interactive, synchronous APIs, low-latency SLAs |
| **Serverless** | Cold-start + low | < 4 MB | Yes (automatic) | Built-in | Intermittent traffic, unpredictable workloads |
| **Asynchronous** | Minutes | Up to 256 MB (S3) | Yes (min=0) | ApproximateBacklogSizePerInstance | Large payloads, long inference (LLM, batch) |

## CPU instance types

| Instance | vCPU | Memory | GPU | Typical models | Cost/hour (on-demand, us-east-1) |
|---|---|---|---|---|---|
| `ml.c5.xlarge` | 4 | 8 GB | — | XGBoost, sklearn, light NLP | ~$0.67 |
| `ml.c5.2xlarge` | 8 | 16 GB | — | Medium tabular, BERT inference | ~$1.34 |
| `ml.c5.4xlarge` | 16 | 32 GB | — | Large tabular, multi-model | ~$2.69 |
| `ml.m5.xlarge` | 4 | 16 GB | — | Memory-intensive tabular | ~$0.69 |
| `ml.m5.4xlarge` | 16 | 64 GB | — | High-throughput batch scoring | ~$2.77 |

## GPU instance types

| Instance | GPU | GPU Memory | vCPU | System Memory | Use case |
|---|---|---|---|---|---|
| `ml.g4dn.xlarge` | 1x T4 | 16 GB | 4 | 16 GB | BERT-base, ResNet, entry-level CV |
| `ml.g5.xlarge` | 1x A10G | 24 GB | 4 | 16 GB | LLM 7B (quantized), CV, Stable Diffusion |
| `ml.g5.2xlarge` | 1x A10G | 24 GB | 8 | 32 GB | LLM 7B-13B with higher throughput |
| `ml.g5.12xlarge` | 4x A10G | 96 GB | 48 | 192 GB | LLM 30B, multi-model GPU serving |
| `ml.g5.48xlarge` | 8x A10G | 192 GB | 192 | 768 GB | LLM 70B, large multi-model |
| `ml.inf2.xlarge` | 1x Inferentia2 | 32 GB | 4 | 16 GB | LLM (Neuron-compiled), cost-efficient |
| `ml.inf2.48xlarge` | 12x Inferentia2 | 384 GB | 192 | 768 GB | LLM 70B at lowest cost/token |

## Auto-scaling target values by workload

| Workload | Instance type | Model latency | Target (InvocationsPerInstance) | Min | Max |
|---|---|---|---|---|---|
| Tabular scoring | ml.c5.xlarge | 30ms | 20 | 2 | 8 |
| Recommendation | ml.c5.xlarge | 50ms | 14 | 2 | 8 |
| NLP classification | ml.c5.2xlarge | 100ms | 7 | 2 | 6 |
| CV inference (GPU) | ml.g5.xlarge | 200ms | 3 | 1 | 4 |
| LLM 7B (GPU) | ml.g5.2xlarge | 500ms | 1 | 1 | 4 |

Formula: `Target = floor(1000 / model_latency_ms * target_utilization)`

Where `target_utilization` is typically 0.6-0.7 (60-70%) to leave headroom
for latency spikes.

## Serverless inference limits

| Parameter | Range | Notes |
|---|---|---|
| MemorySizeInMB | 1024-6144 | Determines CPU allocation (proportional) |
| MaxConcurrency | 1-200 | Max concurrent invocations per endpoint |
| ProvisionedConcurrency | 0-MaxConcurrency | Warm capacity to reduce cold-start; 0 = pure scale-to-zero |
| Payload size | Up to 4 MB | For larger payloads use async inference |
| Timeout | Up to 3 seconds | Inference must complete within 3s |

Cold-start latency: typically 500ms-3s for the first invocation after idle.
Use `ProvisionedConcurrency >= 1` to eliminate cold-start for production
workloads with latency requirements.

## Asynchronous inference limits

| Parameter | Range | Notes |
|---|---|---|
| Payload size | Up to 256 MB (via S3) | Request body uploaded to S3 first |
| Instance count | 0 to N | Min=0 enables scale-to-zero when queue drains |
| Queue | S3-backed | SageMaker manages the queue; visible in CloudWatch |
| Timeout | Up to 15 minutes | Long inference (LLM generation, video processing) |
| Notification | SNS (optional) | Success + error topics |
| Scaling metric | ApproximateBacklogSizePerInstance | Queue depth per instance |

## Container image registries

### SageMaker Deep Learning Containers (DLC)

| Framework | Registry (us-east-1) | Common tags |
|---|---|---|
| PyTorch (CPU) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference | 2.1.0-cpu-py310, 2.0.1-cpu-py310 |
| PyTorch (GPU) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference | 2.1.0-gpu-py310-cu118 |
| TensorFlow (CPU) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-inference | 2.13.0-cpu |
| TensorFlow (GPU) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-inference | 2.13.0-gpu |
| XGBoost | 763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference | 1.7-1 |
| DJL (LLM) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/djl-inference | 0.23.0-deepspeed0.9.5-cu118 |
| HuggingFace (LLM) | 763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-tgi-inference | 2.1.1-tgi1.4.0-gpu |

The registry account ID `763104351884` is the same across all regions.
Change the region in the URI for other regions.

### Custom containers

Build and push to your account's ECR:

```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker build -t <repo>:<tag> .
docker tag <repo>:<tag> <account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>
```

The SageMaker execution role needs `ecr:BatchGetImage` on the ECR repo.

## Execution role permissions

Minimum IAM policy for SageMaker endpoint deployment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::<model-artifact-bucket>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      "Resource": "arn:aws:ecr:<region>:<account-id>:repository/<repo>"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:<region>:<account-id>:key/<key-id>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:AbortMultipartUpload", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::<data-capture-bucket>",
        "arn:aws:s3:::<data-capture-bucket>/*"
      ]
    }
  ]
}
```

Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "sagemaker.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```
