---
description: Train and deploy an Amazon Comprehend custom document classifier with production-grade defaults (multi-class vs multi-label, CSV/Augmented Manifest training data, PLAIN_TEXT vs Native PDF mode, KMS encryption, VPC endpoint, endpoint vs batch inference, auto-scaling, IAM role scoping). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "train comprehend classifier"
  - "deploy comprehend classifier"
  - "comprehend document classifier"
  - "comprehend custom classifier"
  - "multi-class classifier"
  - "multi-label classifier"
  - "comprehend endpoint"
  - "augmented manifest classifier"
  - "native pdf classifier"
  - "batch classification"
  - "comprehend classify documents"
  - "document classifier training"
routes_to: comprehend-classifier-deployer
---

# /aws:deploy-comprehend-classifier

Activate the `comprehend-classifier-deployer` skill and train/deploy
an Amazon Comprehend custom document classifier with production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Multi-class vs multi-label mode selection
2. Training data format (CSV vs Augmented Manifest from Ground Truth)
3. Classifier input mode (PLAIN_TEXT vs Native PDF)
4. Training job (create-document-classifier)
5. Model evaluation metrics (precision, recall, F1)
6. Endpoint deployment and auto-scaling
7. Batch inference job
8. KMS encryption and VPC endpoint
9. IAM roles and versioning
10. Cost optimization and recent features

## When to use

- You need to train a Comprehend custom document classifier.
- You are choosing between multi-class and multi-label classification.
- You need to deploy a real-time endpoint with auto-scaling.
- You need to run batch classification on a large document set.
- You need KMS encryption for model artifacts.
- You need VPC endpoint for private Comprehend inference.
- You need to evaluate model metrics (precision, recall, F1).

## When NOT to use

- **Comprehend pre-trained APIs** (Sentiment, KeyPhrase, Entity) —
  these do not require custom training.
- **Comprehend Custom Entity Recognition** — different service (uses
  entity recognizer, not document classifier).
- **Comprehend Topic Modeling** — unsupervised, no training labels.
- **SageMaker model deployment** — use SageMaker deploy skills.

## How to invoke

### Slash command

```
/aws:deploy-comprehend-classifier
```

Then provide: classifier name, mode (multi-class/multi-label), input
mode (PLAIN_TEXT/Native PDF), training data S3 path, per-class doc
counts, language code, inference mode (endpoint/batch), KMS key ARN,
IAM role ARN, VPC config (if needed), tags.

### Natural language

Any of these routes to the same skill:

- "train a Comprehend document classifier"
- "deploy a multi-class classifier endpoint"
- "run batch classification on my documents"
- "train a Native PDF classifier with KMS"
- "choose between multi-class and multi-label"

### CLI routing

```bash
node cli/bin/cli.js route "train a comprehend document classifier"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to train and deploy
Comprehend classifiers. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-comprehend-classifier

     Train a multi-class classifier named support-ticket-classifier.
     English, CSV at s3://my-bucket/comprehend/training/training.csv.
     5000 docs, 5 classes (min 800 each). Deploy endpoint ticket-endpoint
     with auto-scaling (1-5 units). KMS key abcd1234.

Skill:
  COMPREHEND_CLASSIFIER: support-ticket-classifier (MULTI_CLASS, PLAIN_TEXT)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Mode: MULTI_CLASS
    [✓] Docs per class: min=800 — PASS (≥50)
    [✓] KMS (model + volume): configured
    [✓] Endpoint: ticket-endpoint (1 IU, auto-scaling 1-5)
  VERIFICATION_COMMANDS:
    aws comprehend describe-document-classifier --document-classifier-arn <arn> --region us-east-1
    aws comprehend describe-endpoint --endpoint-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/comprehend-classifier-deployer/SKILL.md`
- Training data and modes guide: `skills/comprehend-classifier-deployer/references/training-data-and-modes.md`
- Endpoint and security guide: `skills/comprehend-classifier-deployer/references/endpoint-and-security.md`
- Eval suite: `skills/comprehend-classifier-deployer/evals/evals.json`
