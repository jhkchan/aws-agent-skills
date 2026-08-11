# Eval: public-image-managed-tls

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — public image (nginx), small power, 2 nodes, managed TLS, health check, environment variables

## Prompt

Create a Lightsail Container Service named web-frontend in
us-east-1. Power: small. Scale: 2 nodes. Container image:
nginx:latest from Docker Hub. Container port 80 mapped to HTTP.
Public endpoint with health check on / every 5 seconds,
threshold 2. Environment variables: ENV=production,
LOG_LEVEL=info. Tags: Environment=production.
