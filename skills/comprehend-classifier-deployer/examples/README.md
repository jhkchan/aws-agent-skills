# End-to-End Example: Comprehend Classifier Deployment

A walkthrough showing how to use the `comprehend-classifier-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are training a multi-class document classifier for support ticket
routing and deploying a real-time endpoint with auto-scaling and KMS
encryption. The classifier needs:

- Classifier name: support-ticket-classifier
- Mode: MULTI_CLASS
- Input: PLAIN_TEXT (CSV training data)
- Training data: s3://my-bucket/comprehend/training/training.csv
  (5000 docs, 5 classes, min 800 docs/class)
- Endpoint: ticket-endpoint (1 inference unit, auto-scaling 1-5)
- KMS: arn:aws:kms:us-east-1:123456789012:key/abcd1234
- IAM role: arn:aws:iam::123456789012:role/ComprehendTrainingRole
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-comprehend-classifier
```

Then paste the requirements.

### Option B: Natural language

```
You: "Train a Comprehend classifier for support ticket routing.
      Multi-class, English, CSV training data at
      s3://my-bucket/comprehend/training/training.csv. 5 classes,
      5000 docs. Deploy endpoint with auto-scaling and KMS."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "train a comprehend document classifier"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
COMPREHEND_CLASSIFIER: support-ticket-classifier (MULTI_CLASS, PLAIN_TEXT)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Classifier name: support-ticket-classifier
  [✓] Classification mode: MULTI_CLASS
  [✓] Input mode: PLAIN_TEXT
  [✓] Training data: s3://my-bucket/comprehend/training/training.csv (CSV, 5000 docs)
  [✓] Docs per class: min=800 — PASS (≥50)
  [✓] Class balance: ratio=1:1 — balanced
  [✓] Language code: en
  [✓] IAM role (training): arn:aws:iam::123456789012:role/ComprehendTrainingRole
  [✓] KMS (model): arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] KMS (volume): arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] VPC config: none (internet-routed training)
  [✓] Inference mode: ENDPOINT (1 inference unit)
  [✓] Endpoint ARN: arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint
  [✓] Auto-scaling: min=1, max=5, target=ApproximateBacklogSize=50
  [✓] Model ARN: arn:aws:comprehend:us-east-1:123456789012:document-classifier/support-ticket-classifier/version/1
  [✓] Tags: Environment=production, Team=support
VERIFICATION_COMMANDS:
  aws comprehend describe-document-classifier --document-classifier-arn <arn> --region us-east-1
  aws comprehend describe-endpoint --endpoint-arn <arn> --region us-east-1
  aws comprehend list-document-classifiers --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Train the classifier (30-90 minutes)
CLASSIFIER_ARN=$(aws comprehend create-document-classifier \
  --document-classifier-name "support-ticket-classifier" \
  --data-format COMPREHEND_CSV \
  --input-data-config S3Uri=s3://my-bucket/comprehend/training/training.csv \
  --document-classifier-config "Mode=MULTI_CLASS,LanguageCode=en" \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendTrainingRole \
  --model-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --volume-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --region us-east-1 \
  --query 'DocumentClassifierArn' --output text)

# Step 2: Wait for training to complete
aws comprehend describe-document-classifier \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --query 'DocumentClassifierProperties.Status' \
  --region us-east-1
# Wait for status: TRAINED

# Step 3: Check evaluation metrics
aws comprehend describe-document-classifier \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --query 'DocumentClassifierProperties.EvaluationMetrics' \
  --region us-east-1

# Step 4: Deploy endpoint
ENDPOINT_ARN=$(aws comprehend create-endpoint \
  --endpoint-name "ticket-endpoint" \
  --model-arn "$CLASSIFIER_ARN" \
  --desired-inference-units 1 \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendEndpointRole \
  --region us-east-1 \
  --query 'EndpointArn' --output text)

# Step 5: Configure auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --min-capacity 1 --max-capacity 5

aws application-autoscaling put-scaling-policy \
  --policy-name "comprehend-scaling" \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":50.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ComprehendApproximateBacklogSize"},"ScaleInCooldown":300,"ScaleOutCooldown":60}'
```

---

## Step 4 — Post-deployment verification

```bash
# Classifier status — should be TRAINED
aws comprehend describe-document-classifier \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --query 'DocumentClassifierProperties.{Status:Status,Metrics:EvaluationMetrics}' \
  --region us-east-1

# Endpoint status — should be IN_SERVICE
aws comprehend describe-endpoint \
  --endpoint-arn "$ENDPOINT_ARN" \
  --query 'EndpointProperties.Status' \
  --region us-east-1

# Test real-time classification
aws comprehend classify-document \
  --endpoint-arn "$ENDPOINT_ARN" \
  --text "I need a refund for invoice #12345" \
  --region us-east-1
# Expected: billing class with high score
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Multi-class vs multi-label | Defaults to multi-class without checking | Explicit mode decision based on category exclusivity | Wrong mode degrades accuracy irreversibly |
| Per-class doc count | Does not verify | Per-class verification with 50-doc minimum | Below 50, model cannot learn |
| Endpoint vs batch | Always picks endpoint | Cost trade-off analysis based on frequency | Batch can be 10x cheaper for periodic workloads |
| KMS encryption | Omits KMS params | Model KMS + volume KMS configured | Without CMK, artifacts use AWS-managed key |
| Native PDF mode | Uses PLAIN_TEXT for PDFs | Native PDF mode for multi-page documents | PLAIN_TEXT loses layout features, 10-15% accuracy loss |
| Auto-scaling | Static instance count | Target tracking with ApproximateBacklogSize | Prevents over-provisioning during low traffic |
| IAM role scoping | Same broad role for all | Separate training, endpoint, and batch roles | Over-privileged endpoint roles are a security risk |

---

## Related artifacts

- **Skill definition:** `skills/comprehend-classifier-deployer/SKILL.md`
- **Training data and modes guide:** `skills/comprehend-classifier-deployer/references/training-data-and-modes.md`
- **Endpoint and security guide:** `skills/comprehend-classifier-deployer/references/endpoint-and-security.md`
- **Slash command:** `commands/aws/deploy-comprehend-classifier.md`
- **Eval suite:** `skills/comprehend-classifier-deployer/evals/evals.json`
- **Legacy test cases:** `skills/comprehend-classifier-deployer/eval/test-cases.yaml`
