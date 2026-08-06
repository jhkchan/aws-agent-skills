# Eval prompt: same-account-source-vpc-ok

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0e5f6789012345678
Service network name: same-account-source-vpc-ok
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0e5f6789012345678
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
      "Sid": "ScopedInvoke",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-service-role"},
      "Action": "vpc-lattice:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceVpc": "vpc-0eee6666bbbb"
        }
      }
    }
  ]
}
```

VPC associations:
  - vpc-0eee6666bbbb (cidr: 10.5.0.0/16, security-group: sg-0eee)

Services:
  - svc-billing (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-billing: type INSTANCE, targets [i-0iii, i-0jjj] in vpc-0eee6666bbbb

RAM resource shares: none
