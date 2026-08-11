---
description: Provision an AWS Client VPN endpoint with production-grade defaults (mutual TLS / Active Directory / SAML federation authentication, authorization rules, target subnet association, split-tunnel vs full-tunnel, DNS, connection logging, self-service portal). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create client vpn endpoint"
  - "deploy client vpn"
  - "client vpn authorization rule"
  - "client vpn mutual tls"
  - "client vpn saml"
  - "client vpn active directory"
  - "client vpn split tunnel"
  - "client vpn full tunnel"
  - "client vpn dns"
  - "client vpn connection logging"
  - "client vpn self-service portal"
  - "client vpn route table"
  - "client vpn"
routes_to: client-vpn-endpoint-deployer
---

# /aws:deploy-client-vpn-endpoint

Activate the `client-vpn-endpoint-deployer` skill and provision an AWS
Client VPN endpoint with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Authentication selection (mutual TLS / Active Directory / SAML)
2. Create the Client VPN endpoint
3. Authorization rules (first-match-wins ordering)
4. Target subnet association (sequential, not concurrent)
5. Routes (propagated + static)
6. DNS configuration (custom DNS for split-tunnel leak prevention)
7. Split-tunnel vs full-tunnel
8. Transport protocol (UDP vs TCP) and port
9. Connection logging (CloudWatch)
10. Security group for target resources
11. Self-service portal
12. CloudWatch metrics (ActiveConnections, AuthenticationFailures)
13. Recent features (SAML federation, self-service portal, IPv6)

## When to use

- You need to create a Client VPN endpoint for remote access.
- You are configuring mutual TLS, Active Directory, or SAML auth.
- You need to set up authorization rules for network access.
- You are enabling split-tunnel with DNS leak prevention.
- You need connection logging to CloudWatch.
- You want to enable the self-service VPN portal.

## When NOT to use

- **AWS Site-to-Site VPN** — use vpn-connection-deployer for site-to-
  site connectivity.
- **Transit Gateway VPN attachments** — use transit-gateway-deployer.
- **Client VPN auditing/troubleshooting** — use VPN audit/troubleshoot
  skills.
- **Security group auditing** — use ec2-security-group-auditor.

## How to invoke

### Slash command

```
/aws:deploy-client-vpn-endpoint
```

Then provide: client CIDR block, authentication type (mutual TLS cert
ARN, AD directory ID, or SAML provider ARN), target VPC and subnets,
DNS server, tunnel mode (split or full), transport protocol, logging
log group, authorization rules (CIDR + group), tags.

### Natural language

Any of these routes to the same skill:

- "create a Client VPN endpoint with mutual TLS"
- "set up SAML federated Client VPN"
- "configure split-tunnel VPN with custom DNS"
- "add authorization rules to my Client VPN"
- "enable the Client VPN self-service portal"

### CLI routing

```bash
node cli/bin/cli.js route "create a client vpn endpoint"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Client VPN
endpoints. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-client-vpn-endpoint

     Create a Client VPN endpoint in us-east-1. Client CIDR
     10.250.0.0/16. Mutual TLS with ACM cert
     arn:aws:acm:us-east-1:123456789012:certificate/abc123.
     Split-tunnel with DNS 10.0.0.2. Associate subnet-aaa11122.
     Authorization rule: allow all groups to 10.0.0.0/16.

Skill:
  CLIENT_VPN: cvpn-aaa11122bbbb3333 (10.250.0.0/16 → vpc-aaa11122)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Client CIDR: 10.250.0.0/16 (non-overlapping)
    [✓] Authentication: mutual-TLS (ACM)
    [✓] Authorization rules: allow-all to 10.0.0.0/16
    [✓] Target subnet: subnet-aaa11122 — available
    [✓] DNS: 10.0.0.2 (split-tunnel leak prevention)
    [✓] Tunnel mode: split-tunnel
  VERIFICATION_COMMANDS:
    aws ec2 describe-client-vpn-endpoints --client-vpn-endpoint-ids <cvpn-id> --region us-east-1
    aws ec2 describe-client-vpn-target-networks --client-vpn-endpoint-ids <cvpn-id> --region us-east-1
```

## References

- Skill definition: `skills/client-vpn-endpoint-deployer/SKILL.md`
- Authentication and authorization guide: `skills/client-vpn-endpoint-deployer/references/auth-and-authorization.md`
- Routes, DNS, and tunnel mode guide: `skills/client-vpn-endpoint-deployer/references/routes-dns-and-tunnel.md`
- Eval suite: `skills/client-vpn-endpoint-deployer/evals/evals.json`
