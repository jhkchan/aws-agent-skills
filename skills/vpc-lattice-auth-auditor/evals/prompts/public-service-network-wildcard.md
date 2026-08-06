# Eval prompt: public-service-network-wildcard

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0b2c3d4e5f6789012
Service network name: public-service-network-wildcard
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0b2c3d4e5f6789012
Owning account: 111111111111

Auth policy state: ACTIVE

Auth policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenInvoke",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "vpc-lattice:*",
      "Resource": "*"
    }
  ]
}
```

VPC associations:
  - vpc-0bbb3333eeee (cidr: 10.2.0.0/16, security-group: sg-0bbb)

Services:
  - svc-payments (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-payments: type INSTANCE, targets [i-0ddd, i-0eee] in vpc-0bbb3333eeee

RAM resource shares: none
