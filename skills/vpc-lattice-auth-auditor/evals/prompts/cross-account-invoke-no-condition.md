# Eval prompt: cross-account-invoke-no-condition

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0c3d4e5f678901234
Service network name: cross-account-invoke-no-condition
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0c3d4e5f678901234
Owning account: 111111111111

Auth policy state: ACTIVE

Auth policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SameAccountAdmin",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/lattice-admin"},
      "Action": "vpc-lattice:*",
      "Resource": "*"
    },
    {
      "Sid": "ExternalInvoke",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/consumer-app"},
      "Action": "vpc-lattice:Invoke",
      "Resource": "*"
    }
  ]
}
```

VPC associations:
  - vpc-0ccc4444ffff (cidr: 10.3.0.0/16, security-group: sg-0ccc)

Services:
  - svc-catalog (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-catalog: type INSTANCE, targets [i-0fff] in vpc-0ccc4444ffff

RAM resource shares:
  - rs-0ccc: shared with account 222222222222
