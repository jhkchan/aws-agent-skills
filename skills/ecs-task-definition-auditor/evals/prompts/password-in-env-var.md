# Eval prompt: password-in-env-var

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: password-in-env-var
networkMode: awsvpc
requiresCompatibilities: ["FARGATE"]
executionRoleArn: arn:aws:iam::111111111111:role/ecs-task-execution
cpu: "512"
memory: "1GB"

containerDefinitions:

```json
[
  {
    "name": "api-server",
    "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/api-server:v2",
    "cpu": 512,
    "memory": 1024,
    "user": "1000",
    "essential": true,
    "environment": [
      {"name": "NODE_ENV", "value": "production"},
      {"name": "DATABASE_PASSWORD", "value": "s3cretP@ssw0rd!2024"},
      {"name": "LOG_LEVEL", "value": "info"}
    ],
    "portMappings": [
      {"containerPort": 3000}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/password-in-env-var",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }
]
```
