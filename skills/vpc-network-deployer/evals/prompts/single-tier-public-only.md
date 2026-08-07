# Eval prompt: single-tier-public-only

Design a deployment plan for a VPC. Emit the standard VERDICT block
(VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Region: ap-southeast-1
- AZ count: 1 (ap-southeast-1a only)
- CIDR: 10.99.0.0/24
- Tiers: public only (single tier — all workloads will run in public
  subnets with internet access)
- NAT strategy: none (no private subnets)
- Endpoints: none (all traffic routes through the Internet Gateway)
- Flow Logs: not required

Workload context: this is intended for a customer-facing microservice
deployment with an Application Load Balancer and ECS Fargate tasks that
need to call external third-party APIs over the internet.
