# Networking skills (39)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `alb-5xx-troubleshooter` | troubleshoot | Diagnoses ALB and NLB 5xx errors (500 InternalServerError, 502 BadGateway, 503 ServiceUnavailable, 504 GatewayTimeout, 561 Unauthorized) through a sys |
| `alb-unhealthy-target-troubleshooter` | troubleshoot | Diagnoses ALB target health check failures through a ten-category diagnostic tree: health check path misconfiguration (wrong path, non-200 response),  |
| `appmesh-deployer` | deploy | Provisions production-grade AWS App Mesh service meshes — mesh with egress filter (DROP_ALL vs ALLOW_ALL), virtual nodes with Cloud Map or DNS service |
| `appmesh-virtual-service-deployer` | deploy | Provisions AWS App Mesh virtual service layer resources with production defaults: service mesh creation (egress filter DROP_ALL vs ALLOW_ALL), virtual |
| `clb-to-alb-migration-operator` | operate | Operates Classic Load Balancer (CLB) to Application Load Balancer (ALB) migrations end-to-end — pre-migration feature assessment (proxy protocol vs X- |
| `client-vpn-endpoint-deployer` | deploy | Provisions AWS Client VPN endpoints with production defaults: mutual TLS certificate auth via ACM, Active Directory and SAML federation, authorization |
| `cloudfront-502-troubleshooter` | troubleshoot | Diagnoses CloudFront 502 and 504 errors via a fourteen-layer decision tree covering origin connection timeouts to ALB/NLB/S3 custom origins, SSL/TLS p |
| `cloudfront-cache-troubleshooter` | troubleshoot | Diagnoses CloudFront caching issues via a symptom-to-cause decision tree covering cache misses on every request, stale content served, unexpected cach |
| `cloudfront-cost-optimizer` | optimize | Optimizes CloudFront distribution costs across nine cost dimensions — Price Class (PriceClass_100 vs PriceClass_200 vs PriceClass_All, where PriceClas |
| `cloudfront-distribution-auditor` | audit | Audits AWS CloudFront distributions for insecure TLS viewer minimum protocol versions and viewer protocol policies, missing Origin Access Control (OAC |
| `cloudfront-distribution-deployer` | deploy | Provisions production-grade CloudFront distributions with secure defaults: Origin Access Control (OAC) for S3 origins (replaces legacy OAI), custom or |
| `cloudfront-invalidation-operator` | operate | Operates CloudFront cache invalidation workflows — invalidation creation with path patterns (/* all, /images/* directory, /images/*.css wildcard, sing |
| `cloudfront-keyvaluestore-deployer` | deploy | Provisions CloudFront KeyValueStore (KVS) with production defaults: KVS creation and key-value pair management, CloudFront Functions integration (read |
| `cloudfront-origin-access-control-deployer` | deploy | Provisions Amazon CloudFront Origin Access Control (OAC) with production defaults: OAC creation (create-origin-access-control), S3 origin configuratio |
| `cloudfront-response-headers-deployer` | deploy | Provisions CloudFront response headers policies with secure defaults: security headers (Content-Security-Policy, Strict-Transport-Security, X-Frame-Op |
| `directconnect-auditor` | audit | Audits AWS Direct Connect (DX) topology for resilience and security posture — physical-layer redundancy (2+ connections at diverse DX locations, not t |
| `elb-cost-optimizer` | optimize | Optimizes Elastic Load Balancer cost across seven dimensions: ALB vs NLB vs CLB cost comparison and migration, LCU (Load Balancer Capacity Unit) analy |
| `elbv2-load-balancer-auditor` | audit | Audits AWS ELBv2 load balancers (ALB/NLB) for insecure TLS listener policies (TLS 1.0/1.1, weak ciphers, cleartext HTTP), disabled access logs, permis |
| `global-accelerator-endpoint-deployer` | deploy | Provisions AWS Global Accelerator with production defaults: accelerator creation with two static anycast IP addresses, listeners (TCP/UDP port ranges) |
| `globalaccelerator-deployer` | deploy | Provisions production-grade AWS Global Accelerator deployments with secure defaults: anycast static IP allocation (Amazon pool or BYOIP), TCP/UDP list |
| `iot-core-thing-deployer` | deploy | Provisions AWS IoT Core things and device pipelines: thing creation, thing type, thing group, device certificate (X.509) with key pair generation, IoT |
| `nat-gateway-traffic-optimizer` | optimize | Optimises NAT Gateway cost through traffic analysis (BytesOutToDestination vs BytesInFromDestination), VPC endpoint elimination of NAT traffic (S3 Gat |
| `networkmanager-core-network-auditor` | audit | Audits AWS Network Manager (Cloud WAN) core networks for detached attachments, permissive resource and segment policies, CIDR overlap across VPC attac |
| `route53-application-recovery-controller-deployer` | deploy | Provisions Route 53 Application Recovery Controller (ARC) with production defaults: recovery cluster (five Route 53 regional clusters across AWS regio |
| `route53-cost-optimizer` | optimize | Optimises Amazon Route 53 DNS cost across seven dimensions: hosted zone cost reduction (consolidating low-traffic domains, detecting unused zones that |
| `route53-dns-troubleshooter` | troubleshoot | Diagnoses Amazon Route 53 DNS resolution failures through a twelve-category diagnostic tree: NS delegation errors (glue records, NS mismatch between r |
| `route53-failover-operator` | operate | Operates Route 53 health checks and DNS failover workflows end-to-end — health-check configuration (endpoint HTTP/HTTPS/TCP, CloudWatch alarm, calcula |
| `route53-health-check-troubleshooter` | troubleshoot | Diagnoses Amazon Route 53 health check and DNS failover failures through a ten-category diagnostic tree: endpoint health check failures (HTTP/HTTPS/TC |
| `route53-record-auditor` | audit | Audits AWS Route 53 record sets for missing health checks on weighted, failover, latency, geolocation, and multivalue routing policies; dangling ALIAS |
| `route53-resolver-deployer` | deploy | Provisions Route 53 Resolver endpoints, forwarding rules, DNS Firewall, and query logging with secure networking defaults. |
| `route53-routing-policy-deployer` | deploy | Provisions Route 53 routing policies and dependent primitives with production defaults: simple, weighted (canary), latency, failover (primary/secondar |
| `transit-gateway-deployer` | deploy | Provisions production-grade AWS Transit Gateway topologies with secure defaults: TGW creation (Amazon ASN, DNS support, multicast), VPC attachments wi |
| `transit-gateway-routing-troubleshooter` | troubleshoot | Diagnoses AWS Transit Gateway routing failures through a fourteen-layer diagnostic tree: TGW route table association vs propagation (separate controls |
| `vpc-connectivity-troubleshooter` | troubleshoot | Diagnoses AWS VPC network connectivity issues through a systematic OSI-layered diagnostic tree: Layer 3 routing (missing route, wrong target IGW/NAT/T |
| `vpc-endpoint-policy-troubleshooter` | troubleshoot | Diagnoses Amazon VPC endpoint policy and connectivity failures across interface endpoints (PrivateLink), Gateway endpoints (S3/DynamoDB), and endpoint |
| `vpc-network-deployer` | deploy | Provisions production-grade VPCs with secure, well-architected network infrastructure: RFC 1918 CIDR planning with growth headroom, multi-AZ public/pr |
| `vpc-peering-deployer` | deploy | Provisions Amazon VPC peering connections with production defaults: requester/accepter model (create-vpc-peering-connection, accept-vpc-peering-connec |
| `vpclattice-service-deployer` | deploy | Provisions Amazon VPC Lattice services with production defaults: service network creation (top-level routing plane), service (HTTP/gRPC), target group |
| `vpn-connection-deployer` | deploy | Provisions AWS Site-to-Site VPN connections with production defaults: customer gateway (CGW), virtual private gateway (VPG) vs transit gateway (TGW) V |
