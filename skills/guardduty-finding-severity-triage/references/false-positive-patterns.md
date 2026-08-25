# False-Positive Patterns — GuardDuty Finding Severity Triage

Quick FP check and detailed FP-1 through FP-6 pattern definitions, moved verbatim from SKILL.md. Load on demand.

## Quick FP check (summary, moved from SKILL.md Step 1)

**Quick FP check** (from the Triage in 30 seconds section): Is the source
an authorized scanner or LB health-checker? → FP-1/FP-2. Is it a DNS
finding on a known-safe domain? → FP-3. Is it Tor traffic on a public
service? → FP-4. Is the caller an AWS service-linked role in normal
scope? → FP-5. Is there a documented change window? → FP-6. If none
match, proceed to Step 2.

The detailed pattern definitions below are for complex or ambiguous cases
where the quick check is inconclusive. Evaluate these patterns in order:

## Detailed false-positive patterns FP-1 through FP-6 (Step 1)

**FP-1: Authorized security scanner.**

Applies to: `Recon:EC2/PortSweepUnusual`, `Recon:EC2/PortProbeUnprotectedPort`,
`Recon:EC2/PortSweep`, `Discovery:EC2/PortSweep`.

All of the following must be true:
- The source IP or instance is identified as an authorized security
  scanner (Nessus, Qualys, Rapid7, internal pentest tool). Source signals:
  the instance is tagged or named with a scanner identifier (e.g.,
  `security-scanner-nessus`, `pentest-kali`), the source IP is within an
  approved pentest CIDR range documented in the account's security runbook,
  or the finding's `additionalInfo` field contains a scanner signature.
- The swept/probed ports are consistent with a vulnerability scan (common
  scan ports: 22, 80, 443, 445, 3389, 1521, 3306, 5432, 6379, 8080, 8443,
  full range 1-65535 for comprehensive scans).

Verdict: **LIKELY_FALSE_POSITIVE**.
Remediation: Archive the finding. Add the scanner's source IP range to
GuardDuty's Trusted IP list (`aws guardduty update-ip-set`) to suppress
future findings of this type from that source.

**FP-2: Load-balancer health-check port sweep.**

Applies to: `Recon:EC2/PortSweepUnusual`, `Discovery:EC2/PortSweep`.

True when the source is an AWS-managed ELB/NLB health checker and the
ports swept match the configured health-check ports. AWS NLB cross-zone
health checks can trigger port-sweep findings because the health checker
probes instances across subnets. Source signals: the source IP is within
AWS ELB health-check IP ranges (published in the AWS IP ranges JSON under
`ELASTICLOADBALANCING`), and the finding's `action.portSweepAction` targets
only the health-check port(s).

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-3: Known-safe DNS domain.**

Applies to: `Trojan:EC2/DGADomainRequest!DNS`, `Trojan:EC2/SuspiciousDomainRequest!DNS`,
`Trojan:EC2/PhishingDomain!DNS`, `Trojan:EC2/PhishingDomainRequest!DNS`.

True when the queried domain is known-safe:
- The domain resolves to or is a subdomain of a major CDN or SaaS platform
  (`cloudfront.net`, `akamai.net`, `fastly.net`, `cloudflare.com`,
  `amazonaws.com`, `googleusercontent.com`).
- The domain is on an organizational allow-list (managed in the security
  team's threat-intel feed).
- The domain is an AWS managed domain (`aws.amazon.com`, `amazonaws.com`,
  `awsstatic.com`, `media-amazon.com`).

**Important:** This FP pattern applies to DNS-request-based findings where
the DGA/suspicious classification is based on domain-name entropy heuristics.
It does NOT apply to findings where the domain is a confirmed phishing or
C2 domain in threat-intel feeds — if the domain appears in a reputable
threat-intel feed, escalate regardless of CDN resemblance.

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-4: Expected Tor traffic on public-facing service.**

Applies to: `UnauthorizedAccess:EC2/TorIPCaller`, `UnauthorizedAccess:EC2/TorClient`.

True when the target resource is a public-facing service designed for
anonymous access:
- An Application Load Balancer, API Gateway, or CloudFront distribution
  serving public content where anonymous/Tor access is expected (e.g., a
  whistleblower portal, anonymous tip line, public API, onion-service
  mirror).
- The service has no authentication requirement (public endpoint) and
  Tor traffic does not violate the application's security posture.

**Important:** If the Tor traffic targets a private/internal service (an
RDS instance, an internal API, an EC2 instance with no public-facing
purpose), this FP does NOT apply — escalate to HIGH. Tor traffic to an
internal service is a strong indicator of reconnaissance or compromise.

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-5: AWS service-linked role activity.**

Applies to: `Discovery:IAMUser/*`, `Recon:IAMUser/*`.

True when the caller identity is an AWS service-linked role or
AWS-internal service principal:
- The caller ARN matches `arn:aws:iam::*:role/aws-service-role/*` or
  `AWSServiceRoleFor*`.
- The API call was made by an AWS service (e.g., AWS Config running a
  configuration snapshot, Security Hub running an aggregation, AWS
  Organizations listing accounts).

These roles are managed by AWS and their API activity is expected.
However, if the service-linked role is performing actions outside its
normal scope (e.g., an `AWSServiceRoleForConfig` calling `iam:CreateUser`),
that is NOT a false positive — it indicates a compromised service role or
an attack using the role's credentials. Escalate to CRITICAL.

Verdict: **LIKELY_FALSE_POSITIVE** (only when activity is within the
service role's expected scope).

**FP-6: Documented change-window behavioral anomaly.**

Applies to: `*:IAMUser/AnomalousBehavior`, `*:EC2/AnomalousBehavior`,
`UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation`.

True when the finding's timestamp falls within a documented change window
(migration, DR drill, scheduled maintenance) AND the anomalous behavior is
consistent with the planned activity:
- A CloudTrail event showing console login from a new country during a
  documented infrastructure migration.
- Unusual API call patterns during a DR failover test.
- Mass IAM permission changes during an organizational restructuring.

The change window must be documented (a change-management ticket, a DR
runbook entry, a migration plan) — not retroactively justified. If the
finding predates the change ticket, the behavior may be the cause of the
change request, not a result of it.

Verdict: **LIKELY_FALSE_POSITIVE** (only when documented change window
is confirmed).

