# Eval prompt: hardened-fargate-task

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: hardened-fargate-task
networkMode: awsvpc
requiresCompatibilities: ["FARGATE"]
executionRoleArn: arn:aws:iam::111111111111:role/ecs-task-execution
taskRoleArn: arn:aws:iam::111111111111:role/app-task-role
cpu: "512"
memory: "1GB"

containerDefinitions:

```json
[
  {
    "name": "web-app",
    "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/web-app:v3",
    "cpu": 512,
    "memory": 1024,
    "memoryReservation": 768,
    "user": "1000:1000",
    "privileged": false,
    "readonlyRootFilesystem": true,
    "essential": true,
    "initProcessEnabled": true,
    "environment": [
      {"name": "NODE_ENV", "value": "production"},
      {"name": "LOG_LEVEL", "value": "info"},
      {"name": "MAX_CONNECTIONS", "value": "100"}
    ],
    "secrets": [
      {
        "name": "DATABASE_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/db-password-AbCdEf"
      },
      {
        "name": "JWT_SIGNING_KEY",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/jwt-key-XyZwVu"
      }
    ],
    "portMappings": [
      {"containerPort": 3000}
    ],
    "linuxParameters": {
      "capabilities": {
        "drop": ["ALL"]
      }
    },
    "dockerSecurityOptions": ["no-new-privileges:true"],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/hardened-fargate-task",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }
]
```
