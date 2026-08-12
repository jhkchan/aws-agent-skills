# End-to-End Example: ECR Replication Deployment

A walkthrough showing how to use the `ecr-replication-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are configuring cross-region ECR replication with pull-through
cache for a multi-region deployment. The setup needs:

- Source registry: 111122223333 in us-east-1
- Cross-region destinations: us-west-2 and eu-west-1 (same account)
- Pull-through cache: docker.io (for third-party base images)
- Lifecycle policies: retain last 30 images per repo in all regions
- Purpose: multi-region DR with cost control

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ecr-replication
```

Then paste the requirements.

### Option B: Natural language

```
You: "Configure ECR cross-region replication from us-east-1 to
      us-west-2 and eu-west-1. Account 111122223333. Also set
      up a pull-through cache for Docker Hub. We need lifecycle
      policies for cost control."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "configure ecr replication"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ECR_REPLICATION: 111122223333 (region: us-east-1) → us-west-2:111122223333, eu-west-1:111122223333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source registry: 111122223333 (region: us-east-1)
  [✓] Replication type: Cross-region (same account)
  [✓] Destinations: us-west-2:111122223333, eu-west-1:111122223333
  [✓] Registry scope: ALL repositories (registry-level)
  [✓] Replicated images: READ-ONLY in destination
  [✓] Pull-through cache rules: docker-hub/ → registry-1.docker.io
  [✓] Replication lag: expected 1-2 minutes (verified ImageReplicationStatus)
  [✓] Storage cost: 3 regions (source + 2 destinations = 3x storage)
  [✓] Batch delete: BLOCKED on replicas (delete at source first)
  [✓] Lifecycle policies: applied in source AND destinations
  [✓] CloudWatch monitoring: ImageReplicationStatus alarm configured
  [✓] Tags: Environment=production, Pattern=multi-region-dr
VERIFICATION_COMMANDS:
  aws ecr describe-registry --region us-east-1
  aws ecr describe-repositories --region us-west-2
  aws cloudwatch get-metric-statistics --namespace AWS/ECR --metric-name ImageReplicationStatus
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Configure cross-region replication (ALL repos)
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-west-2", "registryId": "111122223333"},
          {"region": "eu-west-1", "registryId": "111122223333"}
        ]
      }
    ]
  }' \
  --region us-east-1

# Step 2: Create pull-through cache rule for Docker Hub
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub/ \
  --upstream-registry-url registry-1.docker.io \
  --region us-east-1

# Step 3: Apply lifecycle policies in ALL regions
# (Lifecycle policies must be set per-repository, not per-registry)
for REGION in us-east-1 us-west-2 eu-west-1; do
  for REPO in $(aws ecr describe-repositories --region $REGION \
    --query 'repositories[*].repositoryName' --output text); do
    aws ecr put-lifecycle-policy \
      --repository-name "$REPO" \
      --lifecycle-policy-text file://lifecycle-30-images.json \
      --region $REGION
  done
done

# Step 4: Create CloudWatch alarm for replication failures
aws cloudwatch put-metric-alarm \
  --alarm-name "ECR-Replication-Failures" \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:ecr-alerts" \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify replication configuration
aws ecr describe-registry --region us-east-1 \
  --query 'replicationConfiguration'

# Verify pull-through cache rule
aws ecr describe-pull-through-cache-rules --region us-east-1

# Push a test image and verify replication
docker push 111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Wait for replication lag, then verify in destinations
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=latest \
  --region us-west-2 \
  --registry-id 111122223333 \
  --query 'imageDetails[0].imageTags'

# Test pull-through cache (first pull fetches from Docker Hub)
docker pull 111122223333.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/nginx:latest

# Verify lifecycle policies are applied
aws ecr get-lifecycle-policy \
  --repository-name my-app \
  --region us-west-2 \
  --query 'lifecyclePolicyText'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Replication scope | Per-repo assumption | Registry-level (ALL repos) | Replication is registry-level; per-repo is not possible |
| Replica permissions | Writable assumption | READ-ONLY in destination | Replicated images cannot be pushed or tagged |
| Lifecycle policies | Source only | Applied in ALL regions | Lifecycle policies do not replicate; each region needs its own |
| Storage cost | Single-region cost | 3x cost (source + 2 destinations) | Each destination stores a full copy |
| Pull-through cache URL | docker.io | registry-1.docker.io | Docker Hub's registry API endpoint is registry-1.docker.io |
| Batch delete | Tries on replica | Blocked — delete source first | Replicas are read-only until source is deleted |
| Replication lag | Deploy immediately | Verify ImageReplicationStatus first | Large images may take minutes to replicate |

---

## Related artifacts

- **Skill definition:** `skills/ecr-replication-deployer/SKILL.md`
- **Cross-region and cross-account guide:** `skills/ecr-replication-deployer/references/cross-region-and-cross-account.md`
- **Pull-through cache and cost guide:** `skills/ecr-replication-deployer/references/pull-through-cache-and-cost.md`
- **Eval suite:** `skills/ecr-replication-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ecr-replication-deployer/eval/test-cases.yaml`
