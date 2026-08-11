# Eval: missing-ecr-credentials

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — ECR private image requested but no registry credentials provided

## Prompt

Create a Lightsail Container Service named data-processor in
us-east-1. Power: small. Scale: 1 node. Container image:
123456789012.dkr.ecr.us-east-1.amazonaws.com/processor:v1.0
from ECR private registry. No ECR credentials have been provided.
Container port 8080. Tags: Environment=dev.
