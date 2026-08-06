# Eval prompt: privileged-ec2-sidecar

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: privileged-ec2-sidecar
networkMode: bridge
requiresCompatibilities: ["EC2"]

containerDefinitions:

```json
[
  {
    "name": "sidecar",
    "image": "public.ecr.aws/nginx/nginx:latest",
    "privileged": true,
    "cpu": 256,
    "memory": 512,
    "user": "1000",
    "essential": true,
    "portMappings": [
      {"containerPort": 80, "hostPort": 8080}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/privileged-ec2-sidecar",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }
]
```
