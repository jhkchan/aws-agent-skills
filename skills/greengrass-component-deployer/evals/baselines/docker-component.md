# Baseline (no-skill) — docker-component

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the HARD dependency
> on aws.greengrass.DockerApplicationManager (required for Docker
> image management), the {work:path} volume mount convention (uses
> hardcoded paths instead), the startup-as-long-running-process
> requirement, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the component recipe with a Docker image:

```yaml
Manifests:
  - Artifacts:
      - URI: "docker:edge-ml-processor:latest"
    Lifecycle:
      Startup: |
        docker run -d edge-ml-processor:latest
```

Then deploy:

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/EdgeDevices" \
  --components '{"com.example.EdgeInference": {"componentVersion": "1.0.0"}}'
```

Mount a volume at /mnt/models.
