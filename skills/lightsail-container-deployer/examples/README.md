# End-to-End Example: Lightsail Container Deployment

A walkthrough showing how to use the `lightsail-container-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Lightsail Container Service for a production
API backend pulling from ECR private registry with managed TLS, health
checks, and a custom domain. The service needs:

- Service name: api-service
- Power: medium (2 vCPU, 4 GB RAM per node)
- Scale: 3 nodes (production redundancy)
- Container image: ECR private (123456789012.dkr.ecr.us-east-1.amazonaws.com/api-service:v2.1)
- ECR credentials: IAM access key configured
- Container port: 8080 mapped to HTTP
- Public endpoint with health check on /health
- Custom domain: api.example.com via CNAME
- CloudWatch Logs enabled

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lightsail-container
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Lightsail container service named api-service.
      Medium power, 3 nodes. Pull from ECR private registry.
      Port 8080. Custom domain api.example.com."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a lightsail container service"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LIGHTSAIL_CONTAINER: api-service
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Container service: api-service — power medium, 3 nodes
  [✓] Container image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/api-service:v2.1 — ECR private
  [✓] ECR auth: access key AKIAXXX configured
  [✓] Container port: 8080 → HTTP
  [✓] Public endpoint: HTTPS, managed TLS
  [✓] Health check: /health — interval 5s, threshold 2
  [✓] Scale: 3 nodes — production redundancy
  [✓] Managed TLS: auto-provisioned for default domain
  [✓] Custom domain: api.example.com (CNAME configured)
  [✓] CloudWatch Logs: enabled
  [✓] Tags: Environment=production, Team=backend
VERIFICATION_COMMANDS:
  aws lightsail get-container-services --service-name api-service
  aws lightsail get-container-service-deployments --service-name api-service
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the container service
aws lightsail create-container-service \
  --service-name "api-service" \
  --power medium \
  --scale 3 \
  --tags key=Environment,value=production key=Team,value=backend

# Step 2: Wait for service to be READY
aws lightsail get-container-services \
  --service-name "api-service" \
  --query 'containerServices[0].State'

# Step 3: Create deployment JSON
cat > containers.json << 'EOF'
{
  "api-service": {
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/api-service:v2.1",
    "environment": {
      "ENV": "production",
      "LOG_LEVEL": "info"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
EOF

cat > endpoint.json << 'EOF'
{
  "containerName": "api-service",
  "containerPort": 8080,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "intervalSeconds": 5,
    "path": "/health",
    "successCodes": "200"
  }
}
EOF

# Step 4: Create the deployment (with ECR credentials)
aws lightsail create-container-service-deployment \
  --service-name "api-service" \
  --containers file://containers.json \
  --public-endpoint file://endpoint.json

# Step 5: Add custom domain CNAME (after endpoint is active)
PUBLIC_DOMAIN=$(aws lightsail get-container-services \
  --service-name "api-service" \
  --query 'containerServices[0].currentDeployment.publicEndpoint.containerName' \
  --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DEXAMPLE \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$PUBLIC_DOMAIN"'"}]
      }
    }]
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# Service status — should be READY
aws lightsail get-container-services \
  --service-name "api-service" \
  --query 'containerServices[0].{State:State,Power:Power,Scale:Scale,Url:url}'

# Deployment status — should be ACTIVE
aws lightsail get-container-service-deployments \
  --service-name "api-service" \
  --query 'deployments[0].{State:State,Version:Version}'

# Verify endpoint health
curl -s -o /dev/null -w "%{http_code}" https://api-service.<region>.cs.amazonlightsail.com/health
# Expected: 200
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| ECR auth | Not configured | Access key with ECR read permissions | Lightsail cannot pull private images without credentials |
| Power vs scale | Confused | Power = per-node, scale = replicas | Different dimensions of capacity |
| Redundancy | Scale 1 in production | At least 2 nodes for production | Single node = single point of failure |
| Managed TLS | Manual cert upload | Auto-provisioned | Lightsail manages certs automatically |
| Custom domain | Manual ACM validation | CNAME to public endpoint | TLS auto-extends via CNAME |
| Health check | Default path / | Dedicated /health endpoint | Better application-level health verification |

---

## Related artifacts

- **Skill definition:** `skills/lightsail-container-deployer/SKILL.md`
- **Power and ECR auth guide:** `skills/lightsail-container-deployer/references/power-and-ecr-auth.md`
- **Endpoints and domains guide:** `skills/lightsail-container-deployer/references/endpoints-and-domains.md`
- **Slash command:** `commands/aws/deploy-lightsail-container.md`
- **Eval suite:** `skills/lightsail-container-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lightsail-container-deployer/eval/test-cases.yaml`
