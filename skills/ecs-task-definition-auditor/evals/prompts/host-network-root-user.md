# Eval prompt: host-network-root-user

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: host-network-root-user
networkMode: host
requiresCompatibilities: ["EC2"]

containerDefinitions:

```json
[
  {
    "name": "worker",
    "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/worker:v1",
    "cpu": 256,
    "memory": 512,
    "user": "root",
    "essential": true,
    "environment": [
      {"name": "WORKER_CONCURRENCY", "value": "4"},
      {"name": "QUEUE_NAME", "value": "jobs"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/host-network-root-user",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }
]
```
