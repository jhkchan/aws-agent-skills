# Eval prompt: plan-migration-http-https-clb-ready

Plan the following CLB-to-ALB migration and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
NOTES).

Operation: plan-migration
CLB name: prod-web-clb
Planned ALB name: prod-web-alb
Region: us-east-1
Account: 111111111111

```json
{
  "LoadBalancerName": "prod-web-clb",
  "Scheme": "internet-facing",
  "Subnets": ["subnet-aaa", "subnet-bbb"],
  "SecurityGroups": ["sg-clb-old"],
  "ListenerDescriptions": [
    {"Protocol": "HTTP", "LoadBalancerPort": 80, "InstanceProtocol": "HTTP", "InstancePort": 8080},
    {"Protocol": "HTTPS", "LoadBalancerPort": 443, "InstanceProtocol": "HTTP", "InstancePort": 8080,
     "SSLCertificateId": "arn:aws:acm:us-east-1:111111111111:certificate/abc"}
  ],
  "Policies": [
    {"LBCookieStickinessPolicy": {"CookieExpirationPeriod": 3600}}
  ],
  "HealthCheck": {"Target": "HTTP:8080/healthz", "Interval": 30, "Timeout": 5, "HealthyThreshold": 3, "UnhealthyThreshold": 3},
  "Attributes": {
    "ConnectionDraining": {"Enabled": true, "Timeout": 300},
    "CrossZoneLoadBalancing": {"Enabled": true},
    "AccessLog": {"Enabled": true, "S3BucketName": "prod-clb-logs", "EmitInterval": 5},
    "ConnectionSettings": {"IdleTimeout": 60}
  },
  "ACMCert": {"CertificateArn": "arn:aws:acm:us-east-1:111111111111:certificate/abc", "Status": "ISSUED", "DomainName": "app.example.com"}
}
```
