# Eval prompt: alb-consolidation-multi-path-routing

Optimise the following ALB fleet for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, ACTION_STEPS).

## Scenario

Three ALBs in the same VPC serve related microservices on subdomains
of the same domain. The team wants to reduce the ALB count.

## Known facts

- Region: us-east-1, VPC: vpc-prod (same VPC for all 3 ALBs)
- ALB 1: `api-alb`
  - Serves: api.example.com
  - Listener: HTTPS:443
  - Target group: 6 x EC2 instances (API service)
  - ConsumedLCUs: average 3.5
  - Monthly cost: $16.43 base + $20.44 LCU = $36.87
- ALB 2: `admin-alb`
  - Serves: admin.example.com
  - Listener: HTTPS:443
  - Target group: 2 x EC2 instances (Admin dashboard)
  - ConsumedLCUs: average 1.0
  - Monthly cost: $16.43 base + $5.84 LCU = $22.27
- ALB 3: `static-alb`
  - Serves: static.example.com
  - Listener: HTTPS:443
  - Target group: 4 x EC2 instances (Static file server)
  - ConsumedLCUs: average 4.0
  - Monthly cost: $16.43 base + $23.36 LCU = $39.79
- All 3 ALBs are internet-facing, same scheme, same subnets
- A wildcard certificate for `*.example.com` already exists in ACM
- Cost Explorer total: $98.93/month ($49.29 base + $49.64 LCU)

## Symptom

The FinOps team wants to reduce the $98.93/month ELB bill. The three
ALBs serve the same domain on different subdomains.
