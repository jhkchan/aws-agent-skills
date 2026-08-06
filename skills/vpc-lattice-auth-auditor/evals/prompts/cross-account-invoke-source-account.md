# Eval prompt: cross-account-invoke-source-account

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0d4e5f6789012345
Service network name: cross-account-invoke-source-account
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0d4e5f6789012345
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
      "Sid": "ScopedExternalInvoke",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/log-consumer"},
      "Action": "vpc-lattice:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "222222222222"
        }
      }
    }
  ]
}
```

VPC associations:
  - vpc-0ddd5555aaaa (cidr: 10.4.0.0/16, security-group: sg-0ddd)

Services:
  - svc-logs (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-logs: type INSTANCE, targets [i-0ggg, i-0hhh] in vpc-0ddd5555aaaa

RAM resource shares:
  - rs-0ddd: shared with account 222222222222
