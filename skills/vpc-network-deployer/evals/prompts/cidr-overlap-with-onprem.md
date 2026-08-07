# Eval prompt: cidr-overlap-with-onprem

Design a deployment plan for a production VPC. Emit the standard VERDICT
block (VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Region: us-east-1
- AZ count: 3 (us-east-1a, us-east-1b, us-east-1c)
- CIDR: 10.0.0.0/16
- Tiers: public, private, database
- NAT strategy: HA (one NAT Gateway per AZ)
- VPC Endpoints: S3, DynamoDB (Gateway)

Constraints from network team:

- The on-premises datacenter uses 10.0.0.0/16 (confirmed via Direct
  Connect BGP advertised routes).
- There is a Site-to-Site VPN to the corporate network that also
  advertises 10.0.0.0/16.
- The workload needs private connectivity to on-prem database servers
  in the 10.0.50.0/24 range.
