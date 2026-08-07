# Eval prompt: vpc-no-nat-no-internet

Diagnose the Lambda invocation failure for the following function. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-vpc-no-nat-no-internet` cannot reach
`https://api.stripe.com/charge`. Logs show `connect ETIMEDOUT
3.18.12.63:443` on every invocation. The function was VPC-attached
last week to reach an RDS instance; the RDS path works, but the
external API call started failing at the same time.

```text
FunctionName: fn-vpc-no-nat-no-internet
Qualifier: prod (version 15)
Runtime: python3.12
Timeout: 10
MemorySize: 512
Handler: app.handler
VpcConfig:
  SubnetIds: [subnet-public-a, subnet-public-b]
  SecurityGroupIds: [sg-app]
Execution role: AWSLambdaVPCAccessExecutionRole attached

Subnet context:
  - subnet-public-a: CIDR 10.0.1.0/24, route table route to
    igw-aaa (internet gateway), no NAT route
  - subnet-public-b: CIDR 10.0.2.0/24, route table route to
    igw-aaa, no NAT route

SG sg-app egress: 0.0.0.0/0 all ports (allow all egress)

Recent log pattern:
  https://api.stripe.com/charge ...
  connect ETIMEDOUT 3.18.12.63:443
  Task timed out after 10.00 seconds
```

Lambda functions in public subnets have no internet access — they
receive no public IP, so traffic to the IGW has no return path.
Verify the route-table configuration and recommend the fix.
