# Baseline (no-skill) response: alb-health-check-path-mismatch

This file captures what a generic assistant produces WITHOUT the
ecs-task-troubleshooter skill loaded.

---

Your tasks are being marked unhealthy by the load balancer. The target
group is returning 404 responses on the health check endpoint, which
means the path the ALB is checking does not match what your application
serves.

You should update the target group health check path to match your
application's health endpoint. The application uses `/api/health` but
the ALB is checking `/healthz`. Change the ALB health check path to
`/api/health`.

You may also want to check that the security group allows traffic from
the ALB to the container port. The container listens on 8080 — make
sure the task security group has an inbound rule on port 8080 from the
ALB's security group.
