# Eval: custom-domain-deployment

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — large power, 3 nodes, ECR image, custom domain app.example.com via CNAME, managed TLS extended

## Prompt

Create a Lightsail Container Service named app-prod in
us-east-1. Power: large. Scale: 3 nodes. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/app:v3.0 from ECR
(credentials configured). Container port 443 mapped to HTTP.
Public endpoint with health check on /healthz. Custom domain:
app.example.com via CNAME to the Lightsail public endpoint.
Enable CloudWatch Logs. Tags: Environment=production,
Domain=custom.
