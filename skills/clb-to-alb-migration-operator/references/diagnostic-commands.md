# clb-to-alb-migration-operator — diagnostic commands (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Pagination (elb / elbv2 / route53)

**Pagination:** `elb describe-load-balancers` paginates at 400/page —
drain `--marker`/`--next-marker`. `elbv2 describe-target-groups`
paginates at 400/page. `route53 list-resource-record-sets` paginates at
100/page (use the `--hosted-zone-id`).

## Live-account pre-flight (CLB metadata gate)

1. `aws elb describe-load-balancers --load-balancer-names <clb-name>
   --output json` — capture `Scheme`, `Subnets`, `SecurityGroups`,
   `ListenerDescriptions` (protocol, port, SSLCertificateId),
   `HealthCheck`, `Policies` (sticky, Proxy Protocol), `Attributes`
   (ConnectionDraining, CrossZoneLoadBalancing, AccessLog,
   ConnectionSettings).
2. `aws elb describe-tags --load-balancer-names <clb-name>` — capture
   tags for replicating onto the ALB (`create-tags`).
3. `aws elbv2 describe-load-balancers` (filter by name to confirm the
   ALB doesn't already exist with the planned name).
4. `aws acm list-certificates --certificate-statuses ISSUED --output
   json` — verify each CLB SSL cert ARN resolves to an ACM cert in
   `ISSUED` state, same region. If the cert is IAM-uploaded
   (`arn:aws:iam::...:server-certificate/...`), plan to import or
   re-issue via ACM (ACM-managed renewal is free; IAM cert renewal is
   manual).
5. `aws ec2 describe-subnets --subnet-ids <subnet-1> <subnet-2>` —
   verify AZ spread.
6. `aws ec2 describe-security-groups --group-ids <target-sg>` — verify
   the target SG allows the ALB SG (planned) on the target port.
7. `aws route53 list-resource-record-sets --hosted-zone-id <zone-id>` —
   capture the CLB alias record (alias or CNAME) for cutover planning.
8. `aws cloudwatch get-metric-statistics --namespace AWS/ELB --metric-
   name RequestCount --dimensions Name=LoadBalancerName,Value=<clb>
   --start-time ... --end-time ...` — baseline traffic volume for
   weighted-cutover increments.
