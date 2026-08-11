# Eval prompt: plan-migration-tcp-listener-blocked

Plan the following CLB-to-ALB migration and emit the standard VERDICT
block. The CLB has a TCP listener for a custom binary protocol — ALB
is HTTP/HTTPS only and cannot handle it.

Operation: plan-migration
CLB name: prod-game-clb
Planned ALB name: prod-game-alb
Region: us-east-1

```json
{
  "LoadBalancerName": "prod-game-clb",
  "Scheme": "internet-facing",
  "Subnets": ["subnet-aaa", "subnet-bbb"],
  "ListenerDescriptions": [
    {"Protocol": "HTTPS", "LoadBalancerPort": 443, "InstanceProtocol": "HTTP", "InstancePort": 8080,
     "SSLCertificateId": "arn:aws:acm:us-east-1:111111111111:certificate/abc"},
    {"Protocol": "TCP", "LoadBalancerPort": 4242, "InstanceProtocol": "TCP", "InstancePort": 4242}
  ],
  "Policies": [],
  "HealthCheck": {"Target": "TCP:4242"}
}
```
