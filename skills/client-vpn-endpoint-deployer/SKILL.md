---
name: client-vpn-endpoint-deployer
description: 'Provisions AWS Client VPN endpoints with production defaults: mutual TLS certificate auth via ACM, Active Directory and SAML federation, authorization rules (network CIDR + group access, first-match ordering), route table target subnet associations, DNS custom servers, connection logging to CloudWatch, split-tunnel vs full-tunnel, transport protocol (UDP/TCP), port selection, security group for target resources, self-service portal, session duration, and CloudWatch metrics (ActiveConnections, AuthenticationFailures). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Client VPN endpoint, configuring authorization rules, setting up mutual TLS, enabling SAML federation, or associating subnets. Triggers: create client vpn endpoint, client vpn authorization rule, client vpn mutual tls, client vpn saml, client vpn split tunnel, client vpn dns, client vpn connection logging, client vpn self-service portal.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ec2, acm, and cloudwatch access. Works with Terraform aws_ec2_client_vpn_endpoint / aws_ec2_client_vpn_network_association / aws_ec2_client_vpn_authorization_rule resources and CloudFormation AWS::EC2::ClientVpnEndpoint templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, client-vpn, vpn-endpoint, cloudops, deploy, networking, provisioning, mutual-tls, saml, authorization-rules, split-tunnel, connection-logging
  dependencies: aws-orchestrator
  keywords: aws, client vpn, vpn endpoint, cloudops, deploy, provisioning, mutual tls, acm, saml, active directory, authorization rule, split tunnel, full tunnel, connection logging, self-service portal
  when_to_use: Invoke when the user wants to create an AWS Client VPN endpoint, configure authentication (mutual TLS via ACM, Active Directory, or SAML federation), set up authorization rules for network access, associate target subnets, configure split-tunnel vs full-tunnel, enable connection logging, or enable the self-service VPN portal. Do NOT invoke for AWS Site-to-Site VPN (use vpn-connection-deployer), Transit Gateway VPN attachments, or Client VPN auditing/troubleshooting.
---

# Client VPN Endpoint Deployer

An AWS CloudOps agent skill that provisions AWS Client VPN endpoints
with correct defaults. The skill walks the operator through
authentication (mutual TLS via ACM, Active Directory, SAML federation),
authorization rules (network CIDR + group access, first-match
ordering), target subnet associations, route table propagation, DNS
configuration, split-tunnel vs full-tunnel, transport protocol,
connection logging, and self-service portal, captures topology and
security decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Client VPN endpoint, Client VPN authorization rule, Client VPN
mutual TLS, Client VPN SAML federation, Client VPN split tunnel,
Client VPN route table, Client VPN connection logging, Client VPN
self-service portal.

## STRICT output contract

When this skill is invoked with a Client-VPN-provisioning request
(create an endpoint, configure authorization rules, set up mutual TLS
auth, enable SAML federation, associate subnets, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `CLIENT_VPN:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Authentication selection | Core auth model (mutual TLS / AD / SAML) |
| Step 2 — Create the Client VPN endpoint | Provisioning step |
| Step 3 — Authorization rules | Network CIDR + group access |
| Step 4 — Target subnet association | Route table + connectivity |
| Step 5 — Routes (static and propagated) | Traffic engineering |
| Step 6 — DNS configuration | Custom DNS servers |
| Step 7 — Split-tunnel vs full-tunnel | Tunnel mode decision |
| Step 8 — Transport protocol and port | UDP vs TCP |
| Step 9 — Connection logging | CloudWatch logging |
| Step 10 — Self-service portal | User self-enrollment |
| Step 11 — CloudWatch metrics | Monitoring |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/auth-and-authorization.md | Auth + authorization detail |
| references/routes-dns-and-tunnel.md | Routes, DNS, tunnel mode detail |

## Mindset

**One-line takeaway:** A Client VPN endpoint is a TLS-based VPN that
lets remote clients connect to AWS resources. Authentication gates who
can connect; authorization rules gate what they can reach once
connected. The endpoint needs at least one target subnet association
before clients can connect, and authorization rules are evaluated in
order — the first matching rule wins.

Three misconceptions dominate Client VPN misdesign at provisioning time:

- **"Creating the endpoint is enough."** It is not. After
  `create-client-vpn-endpoint`, the endpoint has no network
  associations. You must associate at least one subnet, which
  provisions a VPN ENI in that subnet. Additionally, you must create
  at least one authorization rule — without it, connected clients
  cannot reach any network.

- **"Authorization rules are cumulative."** They are NOT. Rules are
  evaluated in order — the first rule that matches a user (or group)
  determines access. A broad `0.0.0.0/0` rule placed before a specific
  rule shadows the specific rule. Rule ordering matters; a baseline
  model often places rules in arbitrary order.

- **"Split-tunnel is just a flag."** It is, but the DNS implications
  are significant. With split-tunnel, only VPC-bound traffic goes
  through the VPN tunnel. Without custom DNS servers, DNS queries for
  VPC resources leak to the client's local DNS resolver and fail.

## Configuration dependency graph (novel heuristic)

Client VPN configurations are NOT independent. The endpoint must exist
before authorization rules can be created. Subnet associations must
exist before clients can connect. Authorization rules must exist
before connected clients can reach any network. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Client VPN endpoint | server certificate (ACM) for mutual TLS; client CIDR (RFC1918, /12 to /22) | endpoint is `pending-associate` until a subnet is associated | the VPN endpoint ARN for all subsequent steps |
| Target subnet association | endpoint exists; subnet exists in a VPC | only ONE association per subnet; up to 12 per endpoint (soft limit); associations processed SEQUENTIALLY (concurrency causes failures) | client connectivity (none possible without at least one) |
| Authorization rule | endpoint exists | rules evaluated in ORDER (first match wins); a missing rule means clients reach NOTHING; no reorder API | network access for connected clients |
| Route (static) | endpoint exists; target subnet associated | static routes to CIDRs beyond the VPC require an authorization rule too | reachability to non-VPC CIDRs (peered VPCs, on-prem) |
| Route (propagated) | endpoint exists; target subnet associated | auto-creates routes for the associated subnet's VPC CIDR | automatic VPC CIDR reachability |
| DNS servers | endpoint exists | custom DNS pushed to clients; WITHOUT custom DNS in split-tunnel, VPC DNS queries leak to local resolver | DNS resolution for VPC resources in split-tunnel |
| Security group (target) | VPC exists; target resource SG | endpoint provisions an ENI in each associated subnet; the ENI's SG controls traffic | inbound rules on target resources |
| Connection logging | endpoint exists; CloudWatch log group exists | logging is `false` by default; log group must exist BEFORE enabling | CloudWatch connection logs |
| Self-service portal | endpoint exists; SAML or mutual-TLS auth | portal disabled by default; requires client configuration bundle | user self-enrollment URL |

**The authorization-rule-ordering + missing-default-rule row is the
one a baseline model misses.** Creating the endpoint and associating a
subnet is necessary but NOT sufficient. Without at least one
authorization rule, connected clients cannot reach any network.

**Cross-dependency gotchas:**
- Authorization rules are evaluated in order. First match wins. Place
  broad rules last and specific rules first.
- Split-tunnel with no custom DNS servers causes DNS leaks. Always
  push the VPC DNS resolver (`.2` address) as a custom DNS server.
- The endpoint security group applies to the ENI in each target
  subnet association, not to the endpoint itself. Target resources
  must allow inbound from the association ENI's security group.

## Expert heuristic: authorization rule ordering

A baseline model says "create an authorization rule to allow access."
The correct heuristic recognizes that rules are evaluated in order and
the first match wins — ordering determines effective access.

```text
Authorization rules (evaluated top-down, first match wins):

  Rule 1: CIDR 10.0.0.0/16  → allow group "data-team"     (specific)
  Rule 2: CIDR 0.0.0.0/0    → allow group "all-staff"      (broad)

  User in both groups connecting:
    → Rule 1 matches → access to VPC only (Rule 2 never evaluated)

  User in "all-staff" only:
    → Rule 1 skipped → Rule 2 matches → access to everything

  WRONG ORDER (broad first): broad rule shadows the specific rule
  → all-staff users get full access regardless of data-team rule
```

**Key implication:** always order rules from most-specific to most-
broad. A broad `0.0.0.0/0` allow rule should be the LAST rule.
Reordering requires deleting and recreating rules (no reorder API).

## Expert heuristic: split-tunnel DNS leak prevention

Split-tunnel routes only VPC-relevant traffic through the VPN. Without
custom DNS servers, clients use their local resolver for DNS queries —
including queries for VPC private hostnames — which fail.

```text
Split-tunnel with NO custom DNS (BROKEN):
  Client → DNS query for ip-10-0-1-5.ec2.internal
    → Local resolver (8.8.8.8) → NXDOMAIN → fails

Split-tunnel WITH custom DNS (CORRECT):
  Endpoint config: DnsServers = ["10.0.0.2"]  (VPC .2 resolver)
  Client → DNS query → VPN tunnel → VPC DNS resolver → resolves ✓

Full-tunnel (no DNS leak risk):
  All traffic including DNS goes through tunnel → no custom DNS needed
  Downside: all internet traffic egresses via AWS (cost)
```

**Key implication:** when `SplitTunnel=true`, always set
`DnsServers=["<VPC-DNS-resolver>"]` (the VPC CIDR `.2` address).

## Expert heuristic: mutual TLS certificate-based auth revocation

With mutual TLS, client certificates are issued by a CA registered in
ACM. Revoking a client certificate requires uploading a CRL
(Certificate Revocation List) to the endpoint — there is no
per-certificate revoke API.

```text
Mutual TLS auth flow:
  1. Server certificate (ACM) → endpoint (server side)
  2. Client certificates signed by same CA → distributed to clients
  3. To revoke: generate CRL, upload via import-client-vpn-client-certificate-revocation-list

  aws ec2 import-client-vpn-client-certificate-revocation-list \
    --client-vpn-endpoint-id cvpn-xxx \
    --certificate-revocation-list file://crl.pem
```

**Key implication:** plan for certificate lifecycle management. For
large fleets, SAML federation is often simpler than managing
individual client certificates and CRLs.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Client CIDR block (RFC1918) | Address pool for VPN clients; must NOT overlap VPC CIDR | Confirm CIDR (e.g., `10.250.0.0/16`) does not overlap target VPC |
| Server certificate in ACM (mutual TLS) | Required for mutual TLS authentication | `aws acm describe-certificate --certificate-arn <arn>` |
| Directory ID (AD auth) | Required for AD-based authentication | `aws ds describe-directories` |
| SAML provider ARN (SAML auth) | Required for federated SAML authentication | Verify IAM SAML provider and role |
| Target VPC and subnets identified | Subnet associations require existing subnets | `aws ec2 describe-subnets` |
| CloudWatch log group (if logging) | Connection logging writes to CloudWatch | `aws logs describe-log-groups` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Authentication selection

| Auth type | How it works | Prerequisites | Best for |
|---|---|---|---|
| Mutual TLS | Client cert validated against server CA chain (ACM) | Server cert in ACM; client certs signed by same CA | Machine-to-machine, cert-managed fleets |
| Active Directory | Client authenticates against AWS Managed AD | Directory ID (AWS Directory Service) | Corporate environments with existing AD |
| SAML 2.0 federation | Client authenticates via SAML IdP (Okta, Azure AD) | IAM SAML provider ARN; IAM role for VPN | Federated identity, SSO-enabled organizations |

**Note:** a server certificate in ACM is required for ALL auth types
(it secures the TLS tunnel). The auth type controls user
authentication; the cert handles transport encryption.

Multiple auth types can be enabled simultaneously (mutual TLS + SAML,
or mutual TLS + AD) for mixed fleets.

## Step 2 — Create the Client VPN endpoint

**Mutual TLS authentication:**

```bash
CVPN_ID=$(aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type certificate-mutual-auth \
  --connection-log-options Enabled=true,CloudwatchLogGroup=client-vpn-logs \
  --dns-servers 10.0.0.2 \
  --transport-protocol udp \
  --vpn-port 443 \
  --split-tunnel \
  --description "Corporate Client VPN - mutual TLS" \
  --query 'ClientVpnEndpointId' --output text --region us-east-1)
```

**SAML federated authentication:**

```bash
CVPN_ID=$(aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type federated-authentication \
  --saml-provider-arn arn:aws:iam::123456789012:saml-provider/CorporateIdP \
  --dns-servers 10.0.0.2 \
  --transport-protocol udp \
  --split-tunnel \
  --description "Corporate Client VPN - SAML" \
  --query 'ClientVpnEndpointId' --output text --region us-east-1)
```

Verify the endpoint is `available` before proceeding.

## Step 3 — Authorization rules

Authorization rules determine which networks connected clients can
access, filtered by user/group. At least one rule is REQUIRED for
clients to reach any network.

```bash
# Default allow rule (all Users → VPC CIDR)
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --target-network-cidr 10.0.0.0/16 \
  --authorize-all-groups \
  --description "Allow all groups to access VPC" \
  --region us-east-1

# Group-restricted rule (specific group → broader network)
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --target-network-cidr 0.0.0.0/0 \
  --access-group-id sg-vpn-full-access \
  --description "Full internet access for full-access group" \
  --region us-east-1
```

**Critical:** rules are evaluated in ORDER (first match wins). Place
specific CIDR + group rules BEFORE broad CIDR + all-groups rules. The
API has NO reorder operation — to reorder, delete and recreate.

**Missing authorization rule = connected clients reach NOTHING.** This
is a silent failure; clients connect successfully but cannot reach any
IP.

## Step 4 — Target subnet association

Each target subnet association provisions a VPN endpoint ENI in the
subnet and enables client connectivity through that AZ.

```bash
aws ec2 create-client-vpn-endpoint-target-network-association \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --subnet-id subnet-aaa11122 \
  --region us-east-1
```

**Constraints:**
- One association per subnet; up to 12 per endpoint (soft limit).
- Each association provisions an ENI (consumes a private IP).
- **Concurrency limit:** AWS processes associations SEQUENTIALLY.
  Associating multiple subnets at once may exceed the concurrency
  limit. Associate one subnet, wait for `available`, then the next.

## Step 5 — Routes (static and propagated)

**Propagated routes (automatic):** when a subnet is associated, a
route for the VPC's CIDR is auto-added. No action needed for VPC-
internal reachability.

**Static routes (manual):** for CIDRs beyond the VPC (peered VPCs,
on-premises via TGW/DX):

```bash
aws ec2 create-client-vpn-endpoint-route \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --destination-cidr 172.16.0.0/16 \
  --target-vpc-subnet-id subnet-aaa11122 \
  --region us-east-1
```

**A static route without an authorization rule is unreachable.** Each
destination CIDR needs both a route AND an authorization rule.

## Step 6 — DNS configuration

Custom DNS servers are pushed to clients via the VPN configuration. In
split-tunnel mode, this is CRITICAL for VPC DNS resolution.

```bash
aws ec2 modify-client-vpn-endpoint \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --dns-servers 10.0.0.2 \
  --region us-east-1
```

**The VPC DNS resolver is the `.2` address** of the VPC CIDR (e.g.,
`10.0.0.2` for `10.0.0.0/16`).

## Step 7 — Split-tunnel vs full-tunnel

| Mode | Behavior | DNS risk | Egress cost | When to use |
|---|---|---|---|---|
| Split-tunnel (`--split-tunnel`) | Only VPC CIDR + pushed routes via VPN | DNS leak if no custom DNS | Low | Most corporate VPNs |
| Full-tunnel (no flag) | ALL traffic via VPN | None | High (all user traffic via AWS NAT) | Security-sensitive environments |

**Critical:** when enabling split-tunnel, ALWAYS set `--dns-servers` to
the VPC DNS resolver.

## Step 8 — Transport protocol and port

| Protocol | Port | Behavior | When to use |
|---|---|---|---|
| UDP (default) | 443 | Faster, lower latency; may be blocked by restrictive firewalls | Most environments |
| TCP | 443 | Works through restrictive firewalls/proxies; higher latency | Restrictive networks |

## Step 9 — Connection logging

```bash
# Create the log group BEFORE enabling logging
aws logs create-log-group --log-group-name client-vpn-logs --region us-east-1

# Enable during creation
--connection-log-options Enabled=true,CloudwatchLogGroup=client-vpn-logs
```

Without logging, connection events (including authentication failures)
are not captured.

## Step 10 — Self-service portal

The self-service portal provides a web URL where users download their
VPN client configuration.

```bash
aws ec2 create-client-vpn-endpoint \
  --client-portal-enabled enabled \
  ...

# Get the portal URL
aws ec2 describe-client-vpn-endpoints \
  --client-vpn-endpoint-ids "$CVPN_ID" \
  --query 'ClientVpnEndpoints[0].SelfServicePortalUrl' \
  --region us-east-1 --output text
```

## Step 11 — CloudWatch metrics

Client VPN publishes metrics under `AWS/ClientVPN` namespace.

| Metric | What it measures |
|---|---|
| `ActiveConnections` | Number of active client connections |
| `AuthenticationFailures` | Number of failed client authentications |
| `EgressBytes` / `IngressBytes` | Bytes sent/received through the endpoint |

## Step 12 — Recent features

- **SAML 2.0 federation (2023-2024):** Full SAML-based authentication
  enabling SSO through Okta, Azure AD, etc.
- **Self-service portal (2023-2024):** Web-based portal for user
  self-enrollment and configuration download.
- **Session duration control (2023-2024):** Configurable session
  duration (1-24 hours) before re-authentication. Default 20 hours.
- **IPv6 Client VPN (2024-2025):** IPv6 support for dual-stack
  environments.
- **Performance improvements (2024-2025):** Up to 10,000 concurrent
  connections per endpoint (soft limit).

## NEVER do these things

1. **NEVER create an endpoint without at least one authorization rule.**
   Without a rule, connected clients cannot reach ANY network. This is
   a silent failure; clients connect but route nowhere.

2. **NEVER enable split-tunnel without custom DNS servers.** Without
   `DnsServers` set to the VPC DNS resolver (`.2` address), VPC
   hostname resolution leaks to the client's local resolver and fails.

3. **NEVER overlap the client CIDR with the VPC CIDR.** The client
   address pool must NOT overlap any target VPC CIDR. Use a dedicated
   RFC1918 range (e.g., `10.250.0.0/16`).

4. **NEVER assume authorization rules are order-independent.** Rules
   are evaluated in ORDER — first match wins. A broad `0.0.0.0/0` rule
   before a specific rule shadows it. Order specific-first, broad-last.

5. **NEVER assume subnet associations succeed concurrently.** AWS
   processes associations sequentially. Associate one subnet, wait for
   `available`, then the next.

6. **NEVER create a static route without a corresponding authorization
   rule.** A route controls forwarding; the authorization rule
   controls access. Both are needed for reachability.

7. **NEVER forget connection logging in production.** Without
   `ConnectionLogOptions Enabled=true`, connection events are not
   captured. Create the CloudWatch log group BEFORE enabling logging.

8. **NEVER use the VPC default security group for the Client VPN ENI
   in production.** Create a dedicated SG for the VPN endpoint ENI.

9. **NEVER assume mutual TLS revocation is per-certificate.** Revoking
   a client cert requires generating and uploading a CRL. Plan for CRL
   lifecycle.

10. **NEVER leave session duration at default for security-sensitive
    environments.** Default is 20 hours. Set explicitly (e.g., 1-4h)
    for tighter security.

## Output format

```text
CLIENT_VPN: <endpoint-id> (<client-cidr> → <target-vpc-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Client CIDR: <cidr> (non-overlapping with target VPC)
  [✓|✗] Authentication: mutual-TLS (ACM <cert-arn>) | Active Directory (<dir-id>) | SAML (<provider-arn>)
  [✓|✗] Authorization rules: <count> rule(s) — first-match ordering verified
  [✓|✗] Target subnet association: <subnet-id> in <az> — available
  [✓|✗] Route table: propagated (VPC CIDR) | static routes: <cidr-list>
  [✓|✗] DNS servers: <dns-server-list> (custom DNS for split-tunnel)
  [✓|✗] Tunnel mode: split-tunnel | full-tunnel
  [✓|✗] Transport protocol: udp | tcp (port <port>)
  [✓|✗] Connection logging: enabled (CloudWatch <log-group>) | disabled
  [✓|✗] Self-service portal: enabled (<url>) | disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ec2 describe-client-vpn-endpoints --client-vpn-endpoint-ids <endpoint-id> --region <region>
  aws ec2 describe-client-vpn-target-networks --client-vpn-endpoint-ids <endpoint-id> --region <region>
  aws ec2 describe-client-vpn-routes --client-vpn-endpoint-ids <endpoint-id> --region <region>
```

### Worked example — mutual TLS, split-tunnel, multi-rule

```text
CLIENT_VPN: cvpn-aaa11122bbbb3333 (10.250.0.0/16 → vpc-aaa11122)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Client CIDR: 10.250.0.0/16 (non-overlapping with 10.0.0.0/16)
  [✓] Authentication: mutual-TLS (ACM arn:aws:acm:us-east-1:123456789012:certificate/abc123)
  [✓] Authorization rules: 2 rules — first-match ordering verified (10.0.0.0/16 data-team first; 0.0.0.0/0 all-staff last)
  [✓] Target subnet association: subnet-aaa11122 in us-east-1a — available
  [✓] Route table: propagated (10.0.0.0/16) + static route to 172.16.0.0/16
  [✓] DNS servers: 10.0.0.2 (VPC DNS resolver — split-tunnel DNS leak prevented)
  [✓] Tunnel mode: split-tunnel
  [✓] Transport protocol: udp (port 443)
  [✓] Connection logging: enabled (CloudWatch client-vpn-logs)
  [✓] Self-service portal: enabled (https://self-service.clientvpn.amazonaws.com/...)
  [✓] Tags: Environment=production, Access=corporate
VERIFICATION_COMMANDS:
  aws ec2 describe-client-vpn-endpoints --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
  aws ec2 describe-client-vpn-target-networks --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
  aws ec2 describe-client-vpn-routes --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
```

## Error handling

### Clients connect but cannot reach any IP
- Missing authorization rule. Create at least one
  `authorize-client-vpn-ingress` rule. Without it, clients route nowhere.

### DNS resolution fails for VPC hostnames in split-tunnel
- Custom DNS servers not configured. Set `DnsServers=["<VPC-DNS>"]`.

### Subnet association fails with association limit exceeded
- AWS processes associations sequentially. Wait for existing
  associations to reach `available` before creating new ones.

### Authorization rule shadows specific rule
- Rules are first-match-wins. Delete and recreate in the correct order
  (specific first, broad last).

## Domain

AWS CloudOps / Amazon Client VPN Endpoint Provisioning & Remote Access
Connectivity.

## AWS documentation

- **Client VPN Guide** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/what-is.html
- **Mutual TLS authentication** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/authentication-authrization.html#mutual
- **SAML federation** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/saml-authentication.html
- **Authorization rules** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-working-rules.html
- **Route tables** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-working-routes.html
- **Split-tunnel** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/split-tunnel.html
- **Connection logging** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-logging.html
- **Self-service portal** — https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-self-service-portal.html
