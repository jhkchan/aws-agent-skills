# Eval prompt: aggregate-worst-finding

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: aggregate-worst-finding
networkMode: host
requiresCompatibilities: ["EC2"]

containerDefinitions:

```json
[
  {
    "name": "legacy-service",
    "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/legacy-service:latest",
    "privileged": true,
    "user": "root",
    "essential": true,
    "environment": [
      {"name": "ENV_NAME", "value": "prod"},
      {"name": "API_KEY", "value": "sk-live-abc123secret456"},
      {"name": "ENDPOINT_URL", "value": "https://api.example.com"}
    ],
    "readonlyRootFilesystem": false,
    "linuxParameters": {
      "capabilities": {
        "add": ["SYS_ADMIN"]
      }
    }
  }
]
```
