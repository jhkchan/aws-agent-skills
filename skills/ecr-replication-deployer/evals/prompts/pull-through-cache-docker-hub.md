# Eval: pull-through-cache-docker-hub

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — pull-through cache for docker.io (registry-1.docker.io), prefix docker-hub/, reduces external rate limits and latency

## Prompt

Create an ECR pull-through cache rule for Docker Hub images.
Use the prefix docker-hub/. Upstream registry is docker.io.
We want Lambda and ECS to pull from the cached copy instead
of hitting Docker Hub directly to avoid rate limits. Region
us-east-1, account 111122223333. Tags: Environment=production,
Upstream=docker-hub.
