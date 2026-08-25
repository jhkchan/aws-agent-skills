# Worked examples — lightsail-container-deployer

Extended worked-example material — the full deploy-command sequence for the primary worked example — moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Worked example — deploy commands (moved from SKILL.md)

Deploy commands:

```bash
# 1. Create the container service (small power, 2 nodes for HA)
aws lightsail create-container-service \
  --service-name api-gateway \
  --power small \
  --scale 2 \
  --tags key=Environment,value=production key=Project,value=api-gateway

# 2. Create containers.json with ECR private image + env vars + port
cat > /tmp/containers.json << 'CJSON'
{
  "api-gateway": {
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/api-gateway:v1.2",
    "environment": {
      "NODE_ENV": "production",
      "LOG_LEVEL": "info",
      "PORT": "8080"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
CJSON

# 3. Create endpoint.json with health check
cat > /tmp/endpoint.json << 'EJSON'
{
  "containerName": "api-gateway",
  "containerPort": 8080,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "intervalSeconds": 5,
    "path": "/health",
    "successCodes": "200"
  }
}
EJSON

# 4. Deploy with ECR credentials
aws lightsail create-container-service-deployment \
  --service-name api-gateway \
  --containers file:///tmp/containers.json \
  --public-endpoint file:///tmp/endpoint.json

# 5. Verify the public endpoint
aws lightsail get-container-services \
  --service-name api-gateway \
  --query 'containerServices[0].{State:State,Power:Power,Scale:Scale,Url:publicEndpoint.url}'

# 6. Add custom domain CNAME in Route 53
PUBLIC_DOMAIN=$(aws lightsail get-container-services \
  --service-name api-gateway \
  --query 'containerServices[0].publicEndpoint.url' --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id Z2DEXAMPLEZONE \
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
