# Diagnostic Commands — Route 53 Resolver Deployer

Live-account pre-flight command listing moved verbatim from SKILL.md. Loaded on demand.

## Pre-flight — live-account command listing

1. `aws route53resolver list-resolver-endpoints --max-results 100` —
   confirm the endpoint name does not collide (for create) or matches
   (for update).
2. `aws route53resolver get-resolver-endpoint --resolver-endpoint-id <id>`
   — capture the full endpoint config for snapshot/diff.
3. `aws ec2 describe-subnets --subnet-ids <ids>` — confirm the subnets
   exist, are in distinct AZs, and belong to the target VPC.
4. `aws ec2 describe-security-groups --group-ids <sg-id>` — confirm the
   security group exists and its ingress/egress rules cover UDP/TCP 53
   on the expected CIDRs.
5. `aws ec2 describe-vpc-attribute --vpc-id <vpc> --attribute enableDnsSupport`
   and `--attribute enableDnsHostnames` — confirm both are `true`.
6. `aws route53resolver list-resolver-rules --max-results 100` — for
   forwarding rules, check domain-name overlap and priority.
7. `aws route53resolver list-firewall-rule-group-associations --max-results 100`
   — for DNS Firewall, check priority collisions on the target VPC.
8. `aws logs describe-log-groups --log-group-name-prefix <name>` (for
   CloudWatch) / `aws s3api head-bucket --bucket <name>` (for S3) /
   `aws firehose describe-delivery-stream --delivery-stream-name <name>`
   (for Kinesis) — verify the query log destination exists.
