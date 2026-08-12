# Eval: service-network-http-service

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — service network (top-level routing plane), HTTP service, INSTANCE target group with health check determining routing eligibility, path-based listener rules

## Prompt

Create a VPC Lattice service network named prod-network with
auth type AWS_IAM in us-east-1. Create an HTTP service
payments-svc. Target group tg-stable (INSTANCE type, port 8080,
VPC vpc-aaa11122, health check path /health). Listener on port
80. Path-based rule: /v2/* routes to tg-stable. Default action
routes to tg-stable. Tags: Environment=production.
