# Baseline (no-skill) response: insufficient-context-need-task-arn

This file captures what a generic assistant produces WITHOUT the
ecs-task-troubleshooter skill loaded.

---

Your ECS service is failing. Without knowing more about the failure,
the most common causes are: the task definition is misconfigured, the
containers are crashing, or the service cannot pull images.

Check the ECS console for the failing task's stoppedReason. Look at
the service events to see what is happening. Also check CloudWatch
Logs for application errors.

If the task is being stopped quickly, look at the container exit code.
If it is OOM-killed, increase the memory. If it cannot pull the image,
check the execution role. If the ALB is marking it unhealthy, check
the health check path.

Provide more details about the error you are seeing and I can help
narrow it down.
