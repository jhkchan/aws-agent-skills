# Eval prompt: no-auth-policy-default-open

Audit the following VPC Lattice service network configuration for security
exposure. Emit the standard VERDICT block (SERVICE NETWORK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Service network id: sn-0a1b2c3d4e5f67890
Service network name: no-auth-policy-default-open
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-0a1b2c3d4e5f67890
Owning account: 111111111111

Auth policy state: NOT_SET

VPC associations:
  - vpc-0aaa1111bbbb (cidr: 10.0.0.0/16, security-group: sg-0aaa)
  - vpc-0ccc2222dddd (cidr: 10.1.0.0/16, security-group: sg-0ccc)

Services:
  - svc-api (protocol HTTPS, port 443) — no service-level auth policy
  - svc-orders (protocol HTTPS, port 443) — no service-level auth policy

Target groups:
  - tg-api: type INSTANCE, targets [i-0aaa, i-0bbb] in vpc-0aaa1111bbbb
  - tg-orders: type INSTANCE, targets [i-0ccc] in vpc-0aaa1111bbbb

RAM resource shares: none
