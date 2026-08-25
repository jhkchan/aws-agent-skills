# Power Scale and ECR Auth — Lightsail Container Deployer

Deep reference on power scale selection (per-node CPU/RAM trade-offs),
ECR private registry authentication (IAM access key flow, credential
rotation), cost predictability (all-inclusive pricing model), and the
interaction between power and scale decisions. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Power scale fundamentals

### Per-node capacity table

| Power | vCPU | RAM | Approx. monthly | Use case |
|---|---|---|---|---|
| nano | 0.25 | 0.5 GB | $7 | Dev/testing, static sites |
| micro | 0.5 | 1 GB | $15 | Low-traffic, prototypes |
| small | 1 | 2 GB | $30 | Small production, APIs |
| medium | 2 | 4 GB | $60 | Medium production, workers |
| large | 4 | 8 GB | $115 | High-traffic, compute |
| xlarge | 8 | 16 GB | $225 | ML inference, heavy compute |

### Cost predictability

Lightsail Container Service uses all-inclusive pricing. The monthly
price includes:

- vCPU and RAM (per node)
- Storage (container layer + ephemeral storage)
- Data transfer (within the included monthly allowance)
- Managed TLS certificate
- Public endpoint HTTPS

There are no separate charges for load balancing, TLS, or data
transfer (up to the included allowance). This makes cost prediction
straightforward:

```text
Monthly cost = power_price * node_count

Example:
  small (2 nodes) = $30 * 2 = $60/month
  medium (3 nodes) = $60 * 3 = $180/month
  large (1 node) = $115 * 1 = $115/month
```

### Power vs scale trade-off

```text
Option A: large x 1 node = $115/month
  → More CPU/RAM per container
  → No redundancy (single point of failure)
  → Better for single-threaded, memory-intensive workloads

Option B: medium x 2 nodes = $120/month
  → Less CPU/RAM per container
  → Redundancy (failover capable)
  → Better for production availability

Option C: small x 4 nodes = $120/month
  → Least CPU/RAM per container
  → High redundancy
  → Better for horizontally scalable workloads
```

**Rule of thumb:** For production, prefer at least 2 nodes. The cost
difference between large x 1 and medium x 2 is negligible, but the
availability difference is critical.

## ECR private registry authentication

### Why Lightsail needs explicit credentials

Lightsail Container Service runs containers in a managed environment
that does NOT inherit the IAM role of your AWS account. To pull from
ECR, you must provide an IAM access key (access key ID + secret access
key) with ECR read permissions.

### Creating an IAM user for ECR access

```bash
# Create IAM user
aws iam create-user --user-name lightsail-ecr-reader

# Attach ECR read-only policy
aws iam attach-user-policy \
  --user-name lightsail-ecr-reader \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# Create access key
aws iam create-access-key --user-name lightsail-ecr-reader \
  --query 'AccessKey.{AccessKeyId:AccessKeyId,SecretAccessKey:SecretAccessKey}' \
  --output table
```

### Registering ECR credentials with Lightsail

```bash
aws lightsail register-container-image \
  --service-name "my-app" \
  --label "ecr-creds" \
  --digest "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app@sha256:abc123"
```

### Credential rotation

When the IAM access key is rotated (deactivated or deleted), you must:

1. Create a new access key for the IAM user.
2. Create a new deployment version with the updated credentials.
3. Verify the deployment pulls the image successfully.

```bash
# Old key deactivated — new deployment needed
aws lightsail create-container-service-deployment \
  --service-name "my-app" \
  --containers file://containers-updated-creds.json \
  --public-endpoint file://endpoint.json
```

### Cross-account ECR pulls

If the ECR repository is in a different AWS account, the IAM user must
have permissions on the target account's ECR repository. Use a resource-
based policy on the ECR repository to allow the Lightsail account:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:root"
      },
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
    }
  ]
}
```

## Changing power and scale

### Power change (vertical scaling)

```bash
aws lightsail update-container-service \
  --service-name "my-app" \
  --power medium
```

This triggers a rolling redeploy. Existing containers are replaced
with new power-sized instances. Plan for brief downtime.

### Scale change (horizontal scaling)

```bash
aws lightsail update-container-service \
  --service-name "my-app" \
  --scale 3
```

This also triggers a rolling redeploy. New nodes are added (or removed)
to match the desired scale.

### Combined change

You can change both power and scale in a single update:

```bash
aws lightsail update-container-service \
  --service-name "my-app" \
  --power large \
  --scale 3
```

## Terraform examples

```hcl
resource "aws_lightsail_container_service" "main" {
  name       = "my-app"
  power      = "small"
  scale      = 2
  is_disabled = false

  tags = {
    Environment = "production"
  }
}

resource "aws_lightsail_container_deployment_version" "main" {
  service_name = aws_lightsail_container_service.main.name
  version      = 1

  container {
    container_name = "my-app"
    image          = "nginx:latest"

    environment = {
      ENV       = "production"
      LOG_LEVEL = "info"
    }

    ports = {
      80 = "HTTP"
    }
  }

  public_endpoint {
    container_name = "my-app"
    container_port = 80

    health_check {
      healthy_threshold   = 2
      unhealthy_threshold = 2
      interval_seconds    = 5
      path                = "/"
      success_codes       = "200"
    }
  }
}
```

## Expert heuristic: power scale vs node count trade-off (moved from SKILL.md)

A baseline model says "pick a size and go." The correct heuristic
recognizes that power scale and node count serve different purposes:

```text
Power scale (per-node capacity):
  ├── nano:    0.25 vCPU, 0.5 GB RAM  — dev/testing
  ├── micro:   0.5 vCPU,  1 GB RAM    — low-traffic
  ├── small:   1 vCPU,    2 GB RAM    — small production
  ├── medium:  2 vCPU,    4 GB RAM    — medium production
  ├── large:   4 vCPU,    8 GB RAM    — high-traffic
  └── xlarge:  8 vCPU,   16 GB RAM    — compute-intensive

Node count (horizontal replicas):
  ├── 1 node  — no redundancy (single point of failure)
  ├── 2 nodes — minimum for high availability
  └── 3+ nodes — production-grade redundancy

Cost comparison (approximate monthly):
  large x 1  ≈ medium x 2  ≈ small x 4
  (similar total cost, but HA requires >= 2 nodes)
```

**Key implication:** for production, always use at least 2 nodes for
redundancy. A medium with 2 nodes provides failover; a large with 1
node does not. The cost is similar, but the availability is very
different.

## Expert heuristic: ECR private auth via access key (moved from SKILL.md)

Lightsail Container Service cannot pull from ECR without explicit
credentials. You must create an IAM user or role with an access key
that has `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, and
`ecr:GetAuthorizationToken` permissions.

```text
ECR auth flow:
  1. Create IAM user (or use existing) with ECR read permissions
  2. Generate access key (access key ID + secret access key)
  3. Pass credentials to Lightsail deployment:
     aws lightsail create-container-service-deployment
       --service-name my-service
       --containers file://containers.json
       --public-endpoint file://endpoint.json
  4. In containers.json, specify image as:
     <account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>
  5. Lightsail stores the credentials in the deployment

Note: credentials are per-deployment. Rotating the IAM key
requires a new deployment version.
```

**Key implication:** for ECR private images, the access key must be
valid for the lifetime of the deployment. If the key is deactivated or
deleted, the next deployment pull will fail.

## Step 3 — ECR templates: IAM policy, containers.json, deploy command (moved from SKILL.md)

**IAM policy for ECR read access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    }
  ]
}
```

**containers.json with ECR image and credentials:**

```json
{
  "my-app": {
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0",
    "command": [],
    "environment": {
      "ENV": "production"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
```

**Deploy with ECR credentials:**

```bash
aws lightsail create-container-service-deployment \
  --service-name "my-app" \
  --containers file://containers.json \
  --public-endpoint file://endpoint.json
```

## Step 6 — scale update command (moved from SKILL.md)

```bash
# Scale up to 3 nodes
aws lightsail update-container-service \
  --service-name "my-app" \
  --scale 3
```
