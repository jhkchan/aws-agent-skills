# Diagnostic commands — lightsail-instance-deployer

Pre-flight / diagnostic CLI listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Live-account pre-flight checks (skip if doing offline architecture plan)

1. Verify IAM permissions: `lightsail:CreateInstances`,
   `CreateInstanceSnapshot`, `AttachStaticIp`, `AllocateStaticIp`,
   `CreateLoadBalancer`, `CreateContainerService`, `CreateDistribution`,
   `CreateRelationalDatabase`, `EnableAddOn`, `CreateDnszone`,
   `PeerVpc`, `IsVpcPeered`. For peering also
   `ec2:DescribeVpcPeeringConnections`.
2. Verify the blueprint exists: `aws lightsail get-blueprints --region <region>`
   returns the blueprint ID (OS-only: `amazon_linux_2023`, `ubuntu_22_04`;
   app+OS: `wordpress`, `lamp_8`, `node_js`).
3. Verify the bundle exists and meets the app+OS minimum (if applicable):
   `aws lightsail get-bundles --region <region>`. WordPress requires
   `medium_3_0` (4 GB RAM, 2 CPU, 80 GB SSD) minimum.
4. Verify the AZ exists: `aws lightsail get-regions --include-availability-zones`.
   Lightsail may not support all EC2 AZs in a region.
5. Verify the SSH default key: `aws lightsail download-default-key-pair --region <region>`.
6. For VPC peering, verify the default EC2-VPC exists:
   `aws ec2 describe-vpcs --filters Name=isDefault,Values=true`.
7. For multi-AZ databases, verify the primary and standby AZs are both
   supported by Lightsail in the region.
