# Eval: docker-component

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Docker component with HARD dependency on aws.greengrass.DockerApplicationManager, local volume mount via {work:path}, image cited

## Prompt

Create a Greengrass v2 component com.example.EdgeInference
version 1.0.0 that runs a Docker container (image:
edge-ml-processor:latest). It needs a local volume mount for
model data at {work:path}/models. Deploy to thing group
EdgeDevices (5 devices) in us-east-1. Include the
aws.greengrass.DockerApplicationManager as a HARD dependency
version 2.0.0. Tags: Environment=production, Runtime=docker.
