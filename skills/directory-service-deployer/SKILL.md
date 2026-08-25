---
name: directory-service-deployer
description: 'Provisions AWS Directory Service with production defaults: directory type selection (Managed Microsoft AD, Simple AD, AD Connector), edition sizing (Standard vs Enterprise), VPC/subnet placement (multi-AZ), DNS configuration (conditional forwarders, on-prem resolution), trust relationships (forest trust, external trust, one-way vs two-way), SSO via IAM Identity Center, cross-account directory sharing, LDAPS (secure LDAP with certificate authority), certificate-based auth, snapshot/restore, Multi-Region replication, password policies, security group association. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Managed AD, deploying Simple AD, configuring AD Connector, setting up trust relationships, enabling LDAPS, or integrating with IAM Identity Center. Triggers: create managed microsoft ad, simple ad, ad connector, directory service trust, ldaps, sso iam identity center, directory sharing, multi-region replication.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ds and ec2 access (and cross-account STS assume-role if directory sharing). Works with Terraform aws_directory_service_directory / aws_directory_service_conditional_forwarder / aws_directory_service_log_subscription resources and CloudFormation AWS::DirectoryService::MicrosoftAD / AWS::DirectoryService::SimpleAD templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, directory-service, managed-ad, cloudops, deploy, security, provisioning, ldaps, sso, trust-relationship, multi-region, directory-sharing
  dependencies: aws-orchestrator
  keywords: aws, directory service, managed microsoft ad, simple ad, ad connector, cloudops, deploy, provisioning, trust relationship, ldaps, iam identity center, sso, multi-region replication, directory sharing
  when_to_use: Invoke when the user wants to create an AWS Directory Service directory (Managed Microsoft AD, Simple AD, or AD Connector), configure trust relationships (forest or external), enable LDAPS (secure LDAP), set up SSO via IAM Identity Center, share a directory across accounts, configure Multi-Region replication, or manage password policies. Do NOT invoke for self-managed AD on EC2, AWS Managed Workstations, or third-party LDAP servers.
---

# Directory Service Deployer

An AWS CloudOps agent skill that provisions AWS Directory Service
directories with correct defaults. The skill walks the operator
through directory type selection (Managed Microsoft AD, Simple AD,
AD Connector), edition sizing, VPC/subnet placement, DNS
configuration, trust relationships, SSO via IAM Identity Center,
cross-account directory sharing, LDAPS, snapshot/restore, Multi-
Region replication, password policies, and security group
association, captures all decisions, and emits a READY_TO_DEPLOY
checklist with copy-pasteable verification commands.

## Activation keywords

create Managed Microsoft AD, deploy Simple AD, configure AD
Connector, directory service trust relationship, LDAPS secure LDAP,
SSO IAM Identity Center, directory sharing cross-account, Multi-
Region replication, directory password policy.

## STRICT output contract

When this skill is invoked with a Directory Service provisioning
request (create a Managed AD, deploy Simple AD, configure AD
Connector, set up trust relationships, enable LDAPS, or configure
SSO/sharing/replication, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels
`DIRECTORY_SERVICE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Directory type selection (Managed AD vs Simple AD vs AD Connector) | Core type decision |
| Step 2 — Edition and sizing (Standard vs Enterprise) | Capacity planning |
| Step 3 — VPC and subnet placement (multi-AZ) | Network placement |
| Step 4 — DNS configuration (conditional forwarders) | DNS resolution |
| Step 5 — Trust relationships (forest vs external) | Cross-directory trust |
| Step 6 — LDAPS (secure LDAP with certificate authority) | Secure LDAP |
| Step 7 — SSO via IAM Identity Center | Single sign-on |
| Step 8 — Cross-account directory sharing | Multi-account access |
| Step 9 — Multi-Region replication | DR and multi-region |
| Step 10 — Password policies and security group association | Security posture |
| Step 11 — Snapshot and restore | Backup and recovery |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/trust-and-ldaps.md | Trust + LDAPS detail |
| references/sso-and-sharing.md | SSO + sharing detail |

## Mindset

**One-line takeaway:** AWS Directory Service provides three managed
directory types — Managed Microsoft AD (full AD in AWS), Simple AD
(low-cost directory for basic needs), and AD Connector (proxy to
on-premises AD). The type selection determines cost, capability, and
integration surface. Trust relationships require careful direction.
LDAPS requires managing a certificate authority lifecycle. Each
decision cascades into prerequisites and DNS configuration.

Three misconceptions dominate Directory Service misdesign at
provisioning time:

- **"AD Connector is a replacement for Managed AD."** It is NOT. AD
  Connector is a proxy that redirects authentication requests to your
  on-premises AD. It does NOT store directory data in AWS. If your
  on-premises AD goes down, AD Connector stops working. Choose AD
  Connector when you want to keep on-prem AD as source of truth.
  Choose Managed AD when you need a standalone AD in AWS.

- **"Trust direction does not matter."** It does. A one-way incoming
  trust means the local domain TRUSTS the remote domain (users in
  the remote domain can access resources in the local domain). A
  one-way outgoing trust is the reverse. Getting the direction wrong
  means users cannot access the resources they need, or get access
  they should not have.

- **"LDAPS is just enabling a flag."** It is NOT. LDAPS requires a
  certificate from a trusted Certificate Authority (AWS Private CA
  or an external CA). The certificate must be imported, associated,
  and renewed before expiry. A baseline model enables LDAPS without
  planning the CA lifecycle, leading to expired certificates and
  broken authentication.

## Configuration dependency graph (novel heuristic)

Directory Service configurations are NOT independent. The directory
type determines what features are available. DNS forwarders must
resolve on-premises domains before AD Connector can authenticate.
Trust relationships require both directories to be healthy. Use this
graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Managed Microsoft AD | 2 private subnets in different AZs; VPC DNS enabled | edition CANNOT be changed after creation; size CANNOT be changed | full AD in AWS |
| Simple AD | 2 private subnets in different AZs; VPC DNS enabled | size CANNOT be changed after creation; NO trusts or LDAPS | basic directory for simple use cases |
| AD Connector | 2 private subnets in different AZs; on-prem AD DNS reachable | does NOT store data; depends on on-prem AD; NO trusts or LDAPS | proxy to on-prem AD |
| DNS conditional forwarder | directory ACTIVE; on-prem DNS IPs known | wrong forwarder IPs silently fail (no creation error) | cross-domain DNS resolution |
| Trust relationship | both directories ACTIVE; DNS resolution working | direction CANNOT be changed after creation — must delete and recreate | cross-domain authentication |
| LDAPS | directory ACTIVE; cert from trusted CA (PCA or external) | cert expiry silently breaks LDAPS; clients get TLS errors | secure LDAP queries |
| IAM Identity Center SSO | directory ACTIVE; IAM Identity Center enabled | only ONE directory per account at a time | SSO for console and apps |
| Directory sharing | directory ACTIVE; target account ID known | unsharing breaks accepter account resources | cross-account directory access |
| Multi-Region replication | Managed AD Enterprise; primary directory ACTIVE | replication is one-way (PRIMARY-to-REPLICA); failover is manual | multi-region DR |
| Password policy | directory ACTIVE | changes affect new passwords immediately | password complexity rules |

**The AD-Connector-vs-Managed-AD row is the one a baseline model
misses.** Selecting AD Connector when the user needs trust
relationships or LDAPS is a provisioning failure. The trust-direction
row is another commonly misunderstood configuration. The procedure
below forces an explicit decision on each.

**Cross-dependency gotchas:**
- DNS conditional forwarders must be configured on BOTH sides for
  bidirectional name resolution. A forwarder from A to B does NOT
  automatically create a reverse forwarder.
- Trust relationships require DNS resolution between domains FIRST.
  Creating a trust without DNS resolution fails silently.
- LDAPS certificate expiry is the #1 cause of sudden authentication
  failures. Monitor expiry and set up renewal alerts.
- IAM Identity Center can connect to only one directory per account.
- Multi-Region replication requires Enterprise edition.

## Expert heuristic: AD Connector vs Managed AD routing

Expert heuristic — AD Connector vs Managed AD routing decision tree (on-prem source of truth, greenfield, basic needs; Simple AD constraints) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it before Step 1 type selection.

## Expert heuristic: trust direction (one-way vs two-way)

Expert heuristic — trust direction semantics (one-way incoming/outgoing, two-way, external vs forest scope) moved verbatim to [references/trust-and-ldaps.md](references/trust-and-ldaps.md).
Load it when Step 5 asks for a trust direction.

## Expert heuristic: LDAPS certificate authority lifecycle

Expert heuristic — LDAPS certificate authority lifecycle (PCA/external CA issuance, register-certificate, enable-ldaps, expiry monitoring, silent breakage) moved verbatim to [references/trust-and-ldaps.md](references/trust-and-ldaps.md).
Load it when Step 6 enables LDAPS.

## Expert heuristic: Multi-Region replication conflict resolution

Expert heuristic — Multi-Region replication conflict resolution (manual failover, RPO gap, old-primary re-add as replica, last-writer-wins, split-brain rules) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when Step 9 configures replication.

## Expert heuristic: DNS forwarder — stub zone vs conditional forwarder

Expert heuristic — stub zone vs conditional forwarder decision rule (single remote domain, multi-forest delegation, AD Connector constraint) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when Step 4 configures cross-domain DNS.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC with DNS resolution enabled | Directory Service requires VPC DNS support | `aws ec2 describe-vpc-attribute --vpc-id <vpc> --attribute enableDnsSupport` |
| 2 private subnets in different AZs | Multi-AZ directory requires subnets in different AZs | `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc>` |
| VPN/DX connectivity (AD Connector) | AD Connector must reach on-prem AD DNS | Verify network connectivity |
| On-prem AD DNS IPs (AD Connector) | AD Connector needs DNS server IPs at creation | Confirm DNS server addresses |
| Certificate from trusted CA (LDAPS) | LDAPS requires valid TLS certificate | Verify certificate in ACM |
| IAM Identity Center enabled (SSO) | SSO requires IAM Identity Center | `aws sso-admin list-instances` |
| Both directory IDs (trust) | Trust requires two active directories | `aws ds describe-directories` |
| Enterprise edition (replication) | Multi-Region replication requires Enterprise | `aws ds describe-directories --directory-id <id>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Directory type selection (Managed AD vs Simple AD vs AD Connector)

| Feature | Managed Microsoft AD | Simple AD | AD Connector |
|---|---|---|---|
| Directory data in AWS | Yes (full AD) | Yes (basic LDAP) | No (proxy) |
| Trust relationships | Supported | NOT supported | NOT supported |
| LDAPS | Supported | NOT supported | NOT supported |
| SSO (IAM Identity Center) | Supported | Supported | Supported |
| Multi-Region replication | Enterprise only | NOT supported | NOT supported |
| Schema extensions | Supported | NOT supported | NOT supported |

**Decision logic:**
- Need trusts, LDAPS, or schema extensions → Managed Microsoft AD
- Simple, low-cost directory, no advanced features → Simple AD
- Keep on-prem AD as source of truth, need AWS auth → AD Connector

## Step 2 — Edition and sizing (Standard vs Enterprise)

| Type / Edition | Max users | Multi-Region | Cost |
|---|---|---|---|
| Managed AD Standard | ~5,000 | NOT supported | Lower |
| Managed AD Enterprise | ~50,000+ | Supported | Higher |
| Simple AD Small | ~500 | N/A | Lowest |
| Simple AD Large | ~5,000 | N/A | Low |

**Edition CANNOT be changed after creation.** If there is any chance
of needing Multi-Region replication or more than 5,000 users, choose
Enterprise from the start. Simple AD size also CANNOT be changed.

## Step 3 — VPC and subnet placement (multi-AZ)

All Directory Service types require at least 2 private subnets in
different Availability Zones.

Subnet/AZ verification and VPC DNS enablement commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them when verifying the multi-AZ placement prerequisites.

**Common mistake:** creating a directory in public subnets. Directory
Service requires PRIVATE subnets. Domain controllers should never be
directly internet-accessible.

## Step 4 — DNS configuration (conditional forwarders)

DNS conditional forwarders enable cross-domain name resolution. They
are required for trust relationships to function.

```bash
# Create a conditional forwarder (AWS directory → on-prem domain)
aws ds create-conditional-forwarder \
  --directory-id d-aaa111222 \
  --remote-domain-name corp.example.com \
  --dns-ip-addrs 10.0.1.53 10.0.2.53 \
  --region us-east-1
```

**Critical:** conditional forwarders must be created on BOTH sides
for bidirectional resolution. Creating a forwarder from A to B does
NOT automatically create a reverse forwarder.

**AD Connector DNS:** AD Connector requires on-prem AD DNS server IPs
at creation via `--dns-ip-addrs`.

## Step 5 — Trust relationships (forest vs external)

| Trust type | Scope | Use case |
|---|---|---|
| Forest trust | Between two entire forests | Enterprise-wide trust |
| External trust | Between two specific domains | Limited trust |

Trust creation and verification commands (create-trust, describe-trusts, expected TrustState Verified) moved verbatim to [references/trust-and-ldaps.md](references/trust-and-ldaps.md).
Load them when emitting the trust provisioning checklist.

**Prerequisites for trust:**
- DNS conditional forwarders on BOTH sides
- Both directories ACTIVE and healthy
- Network connectivity between directories

## Step 6 — LDAPS (secure LDAP with certificate authority)

LDAPS enables encrypted LDAP communication. Only Managed Microsoft AD
supports LDAPS.

LDAPS commands (register-certificate, enable-ldaps, list-certificates, ACM expiry query) moved verbatim to [references/trust-and-ldaps.md](references/trust-and-ldaps.md).
Load them when enabling LDAPS or monitoring certificate expiry.

**Critical:** if the certificate expires, LDAPS breaks silently.
Clients get TLS errors but the directory appears healthy. Set up
CloudWatch alarms on the `DaysToExpiry` metric.

## Step 7 — SSO via IAM Identity Center

IAM Identity Center can use a Directory Service directory as an
identity source for SSO.

**Via AWS Console (IAM Identity Center > Settings > Identity source):**
1. Select "AWS Directory Service" as the identity source.
2. Select the directory from the dropdown.
3. Users and groups are managed within the directory.

**Constraint:** IAM Identity Center can connect to only ONE directory
at a time per account. Switching directories disconnects all existing
SSO users and permission sets.

## Step 8 — Cross-account directory sharing

Directory sharing allows other AWS accounts to access a directory
managed in your account. Only Managed Microsoft AD can be shared.

Directory sharing commands (share-directory, accept-shared-directory, describe-shared-directories) moved verbatim to [references/sso-and-sharing.md](references/sso-and-sharing.md).
Load them when emitting the sharing checklist.

**Constraints:** Unsharing breaks all accepter-account resources that
reference the directory.

## Step 9 — Multi-Region replication

Multi-Region replication creates a read-only replica of a Managed
Microsoft AD in another region. Requires Enterprise edition.

```bash
# Add a region to the existing directory
aws ds add-region \
  --directory-id d-aaa111222 \
  --region us-west-2 \
  --vpc-settings VpcId=vpc-bbb22233,SubnetIds=subnet-xxx,subnet-yyy
```

**Failover is a manual promotion** (not automatic). The old primary
becomes a replica if still available.

**Constraints:**
- Replication is PRIMARY-to-REPLICA only (one-way)
- Requires Enterprise edition — Standard does NOT support it

## Step 10 — Password policies and security group association

```bash
# Update the directory password policy
aws ds update-password-policy \
  --directory-id d-aaa111222 \
  --min-password-length 12 \
  --require-uppercase true \
  --require-lowercase true \
  --require-numbers true \
  --require-symbols true \
  --password-history 24 \
  --max-password-age 90 \
  --region us-east-1
```

Required AD ports for security group rules:

| Port | Protocol | Purpose |
|---|---|---|
| 53 | TCP/UDP | DNS |
| 88 | TCP/UDP | Kerberos authentication |
| 389 | TCP/UDP | LDAP |
| 445 | TCP | SMB (Group Policy) |
| 464 | TCP/UDP | Kerberos password change |
| 636 | TCP | LDAPS (secure LDAP) |
| 3268 | TCP | Global Catalog LDAP |
| 49152-65535 | TCP | Dynamic RPC |

## Step 11 — Snapshot and restore

Snapshot and restore commands (create-snapshot, restore-from-snapshot, describe-snapshots) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them when backup or restore is in scope.

**Constraints:** Restore replaces the current directory state (full
overwrite). Directory is unavailable during restore (1-2 hours).

## Step 12 — Recent features

Step 12 recent features (IAM Identity Center deep integration, replication improvements, LDAPS for DC replication, Organizations bulk sharing, password-policy enforcement) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when a request involves a 2023+ capability.

## NEVER do these things

1. **NEVER select AD Connector when trust relationships or LDAPS are
   needed.** AD Connector does NOT support trusts or LDAPS. It is a
   proxy, not a full directory. Choose Managed Microsoft AD.

2. **NEVER create a directory with Standard edition if Multi-Region
   replication might be needed.** Edition CANNOT be changed after
   creation. Choose Enterprise from the start.

3. **NEVER create a trust relationship without conditional forwarders
   on BOTH sides.** Trust requires DNS resolution between domains
   first. Without bidirectional forwarders, the trust does not
   function.

4. **NEVER get the trust direction wrong.** One-Way: Incoming means
   remote users access local resources. One-Way: Outgoing means local
   users access remote resources. Direction CANNOT be changed after
   creation.

5. **NEVER enable LDAPS without planning the certificate authority
   lifecycle.** Certificates expire silently breaking LDAPS. Use AWS
   PCA for automatic renewal or set up CloudWatch alarms on
   `DaysToExpiry`.

6. **NEVER create a directory in public subnets.** Directory Service
   requires PRIVATE subnets. Domain controllers should never be
   directly internet-accessible.

7. **NEVER assume IAM Identity Center can use multiple directories
   simultaneously.** Only ONE directory per account at a time.

8. **NEVER assume AD Connector works when on-prem AD is down.** AD
   Connector is a proxy — it depends on the on-prem AD for all
   authentication.

9. **NEVER create a Simple AD when schema extensions or certificate-
   based auth is needed.** Simple AD does NOT support these. Choose
   Managed Microsoft AD.

10. **NEVER forget to verify the directory is ACTIVE before creating
    trusts, enabling LDAPS, or configuring SSO.** All dependent
    configurations require the directory to be in ACTIVE state.

## Output format

```text
DIRECTORY_SERVICE: <directory-id> (<type>, <edition>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Directory type: Managed Microsoft AD | Simple AD | AD Connector
  [✓|✗] Edition/Size: Standard | Enterprise (Small | Large for Simple AD)
  [✓|✗] VPC: <vpc-id> (enableDnsSupport=true, enableDnsHostnames=true)
  [✓|✗] Subnet AZ1: <subnet-id> (<az>)
  [✓|✗] Subnet AZ2: <subnet-id> (<az>)
  [✓|✗] DNS name: <directory-dns-name>
  [✓|✗] NetBIOS name: <short-name>
  [✓|✗] DNS conditional forwarders: configured (both sides) | not needed
  [✓|✗] Trust relationship: <type> <direction> to <remote-domain> | not needed
  [✓|✗] LDAPS: enabled (cert from <CA>, expires <date>) | disabled
  [✓|✗] IAM Identity Center SSO: connected | not configured
  [✓|✗] Directory sharing: shared with <account-ids> | not shared
  [✓|✗] Multi-Region replication: replica in <region> | not configured
  [✓|✗] Security group: <sg-id> (required ports open)
  [✓|✗] Password policy: min-length=<n>, complexity=<on|off>, max-age=<days>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ds describe-directories --directory-ids <directory-id> --region <region>
  aws ds describe-trusts --directory-id <directory-id> --region <region>
  aws ds list-certificates --directory-id <directory-id> --region <region>
```

### Worked example — Managed Microsoft AD with trust and LDAPS

```text
DIRECTORY_SERVICE: d-aaa111222 (ManagedMicrosoftAD, Enterprise)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Directory type: Managed Microsoft AD
  [✓] Edition/Size: Enterprise
  [✓] VPC: vpc-aaa11122 (enableDnsSupport=true, enableDnsHostnames=true)
  [✓] Subnet AZ1: subnet-aaa111 (us-east-1a)
  [✓] Subnet AZ2: subnet-bbb222 (us-east-1b)
  [✓] DNS name: corp.example.com
  [✓] NetBIOS name: corp
  [✓] DNS conditional forwarders: configured (both sides)
  [✓] Trust relationship: Forest Two-Way to onprem.example.com
  [✓] LDAPS: enabled (cert from AWS PCA, expires 2026-12-01)
  [✓] IAM Identity Center SSO: connected
  [✓] Directory sharing: not shared
  [✓] Multi-Region replication: not configured
  [✓] Security group: sg-directory111 (ports 53/88/389/445/636/3268 open)
  [✓] Password policy: min-length=12, complexity=on, max-age=90
  [✓] Tags: Environment=production, ManagedBy=cloudops
VERIFICATION_COMMANDS:
  aws ds describe-directories --directory-ids d-aaa111222 --region us-east-1
  aws ds describe-trusts --directory-id d-aaa111222 --region us-east-1
  aws ds list-certificates --directory-id d-aaa111222 --region us-east-1
```

## Error handling

Error-handling deep dives (directory stuck in CREATING, trust stuck in CREATING/FAILED, LDAPS failing despite enabled, AD Connector auth failures, IAM Identity Center SSO failures) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load them when a deployment or verification step fails.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert heuristics (AD Connector vs Managed AD routing, Multi-Region replication conflict resolution, stub zone vs conditional forwarder) and Step 12 recent features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — VPC/subnet/DNS verification commands and snapshot/restore commands moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — provisioning failure deep dives moved from SKILL.md
- [references/trust-and-ldaps.md](references/trust-and-ldaps.md) — trust and LDAPS fundamentals, expert heuristics, and CLI (moved content appended)
- [references/sso-and-sharing.md](references/sso-and-sharing.md) — SSO, sharing, permission sets, and sharing CLI (moved content appended)

## Domain

AWS CloudOps / AWS Directory Service Provisioning & Identity
Management.

## AWS documentation

- **AWS Directory Service** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/what_is.html
- **Managed Microsoft AD** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_microsoft_ad.html
- **Simple AD** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_simple_ad.html
- **AD Connector** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_ad_connector.html
- **Trust relationships** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_setup_trust.html
- **LDAPS (Secure LDAP)** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_ldap.html
- **IAM Identity Center** — https://docs.aws.amazon.com/singlesignofforlogin/latest/UserGuide/what-is.html
- **Directory sharing** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_directory_sharing.html
- **Multi-Region replication** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_multi_region.html
- **Password policies** — https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_password_policy.html
