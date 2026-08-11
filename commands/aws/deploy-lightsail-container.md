---
description: Provision an Amazon Lightsail Container Service with production-grade defaults (power scale nano-xlarge, node count for redundancy, ECR private registry auth, public endpoint with managed TLS, health checks, environment variables, secrets, custom domain via CNAME, CloudWatch Logs). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lightsail container"
  - "deploy lightsail container"
  - "lightsail container service"
  - "lightsail power scale"
  - "lightsail ecr auth"
  - "lightsail container deployment"
  - "container public endpoint"
  - "lightsail managed tls"
  - "lightsail custom domain"
  - "lightsail environment variables"
  - "lightsail secrets"
  - "lightsail scale"
routes_to: lightsail-container-deployer
---

# /aws:deploy-lightsail-container

Activate the `lightsail-container-deployer` skill and provision an
Amazon Lightsail Container Service with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Container service creation (power scale nano-xlarge)
2. Container deployment (image from ECR or public registry)
3. ECR private registry auth (IAM access key)
4. Public endpoint (HTTPS, managed TLS, health check)
5. Environment variables and secrets
6. Scale (node count for horizontal capacity)
7. Managed TLS certificate (auto-provisioned)
8. Custom domain via DNS CNAME
9. CloudWatch Logs integration
10. Recent features (xlarge power, VPC peering, deployment rollback)

## When to use

- You need to create a Lightsail Container Service.
- You are deploying a container image from ECR or public registry.
- You need to configure ECR private registry auth.
- You need a public endpoint with managed TLS.
- You need environment variables or secrets.
- You need to set up a custom domain.
- You need to scale horizontally (node count).

## When NOT to use

- **ECS/EKS** — complex orchestration needs ECS or EKS skills.
- **App Runner** — for fully managed container deployment without
  power/scale management.
- **Lambda** — serverless functions.
- **Elastic Beanstalk** — PaaS with web/app server management.

## How to invoke

### Slash command

```
/aws:deploy-lightsail-container
```

Then provide: service name, power scale, node count, container image
URI, ECR credentials (if private), container port, health check path,
environment variables, secrets, custom domain, tags.

### Natural language

Any of these routes to the same skill:

- "create a lightsail container service"
- "deploy a container on lightsail"
- "set up a lightsail container with ECR"
- "configure lightsail managed TLS and custom domain"
- "scale my lightsail container service"

### CLI routing

```bash
node cli/bin/cli.js route "create a lightsail container service"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Lightsail
Container Service resources. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-lightsail-container

     Create a Lightsail container service named api-service.
     Medium power, 3 nodes. Pull from ECR. Port 8080.
     Custom domain api.example.com.

Skill:
  LIGHTSAIL_CONTAINER: api-service
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Container service: api-service — power medium, 3 nodes
    [✓] Container image: ECR private
    [✓] ECR auth: access key configured
    [✓] Container port: 8080 → HTTP
    [✓] Public endpoint: HTTPS, managed TLS
    [✓] Custom domain: api.example.com (CNAME)
  VERIFICATION_COMMANDS:
    aws lightsail get-container-services --service-name api-service
```

## References

- Skill definition: `skills/lightsail-container-deployer/SKILL.md`
- Power and ECR auth guide: `skills/lightsail-container-deployer/references/power-and-ecr-auth.md`
- Endpoints and domains guide: `skills/lightsail-container-deployer/references/endpoints-and-domains.md`
- Eval suite: `skills/lightsail-container-deployer/evals/evals.json`
