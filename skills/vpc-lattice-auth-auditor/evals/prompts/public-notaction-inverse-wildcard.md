# Eval prompt: public-notaction-inverse-wildcard

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0f6789012345678901
Service network name: public-notaction-inverse-wildcard
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0f6789012345678901
Owning account: 111111111111

Auth policy state: ACTIVE

Auth policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InverseWildcard",
      "Effect": "Allow",
      "Principal": "*",
      "NotAction": [
        "vpc-lattice:GetService",
        "vpc-lattice:ListServiceNetworks"
      ],
      "Resource": "*"
    }
  ]
}
```

VPC associations:
  - vpc-0fff7777cccc (cidr: 10.6.0.0/16, security-group: sg-0fff)

Services:
  - svc-search (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-search: type INSTANCE, targets [i-0kkk] in vpc-0fff7777cccc

RAM resource shares: none
