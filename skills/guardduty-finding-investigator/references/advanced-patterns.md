# Advanced Patterns — GuardDuty Finding Investigator

Expert-knowledge deep dives, Step-0 non-obvious behaviours, and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Step 0: Non-obvious behaviours that change the diagnosis

- **A finding from a "trusted" source IP is still a finding until the
  IP is in the trusted IP list.** GuardDuty does not deduce trust from
  on-prem CIDRs, SaaS ranges, or scanner hostnames. Prefer the Trusted
  IP list over suppression — the trusted IP list lets GuardDuty keep
  tracking the source's behaviour.

- **ConsoleLogin from a new AWS Region fires on the first successful
  login from that Region.** Travelling users trigger this once per
  Region. Either add their CIDRs to the trusted IP list, or accept the
  Low severity noise — never blanket-suppress.

- **CryptoCurrency:EC2/BitcoinTool.B!DNS fires on DNS, not on the
  binary.** A misconfigured app calling a domain that resolves to a
  pool will trigger. Corroborate with CloudWatch CPUUtilization before
  isolating.

- **Policy:IAMUser/S3BucketAnonymousGranted fires even for intentional
  public buckets** (website bucket, CloudFront origin). Confirm the
  change author and ticket, then suppress if intentional.

- **Runtime:EC2/ProcessA findings require the GuardDuty Security
  Agent installed.** If the agent is disabled or unsupported, Runtime
  findings will not fire — absence does not mean absence of runtime
  threats. EKS findings may originate from the host node (privileged
  DaemonSet), not the workload pod — inspect
  `resource.eksClusterDetails` and `resource.containerDetails`.

- **VPC Flow Logs capture only L3/L4 traffic.** DNS-over-HTTPS,
  encrypted C2, and tunneled egress look like benign TLS on port 443.
  For Backdoor/CryptoCurrency, supplement with Route 53 Resolver logs
  (DNS) and Malware Protection scans. Suppression filters using
  `equals` on the resource ARN break when the resource is recreated —
  use `equals` on the static attribute (instance profile, IAM user
  name, bucket name).

## Expert heuristic (moved from SKILL.md)

When triaging a finding, ask three questions in order. (1) Does the
finding's `service.action` field match the resource type? A
`networkConnectionAction` on an `AccessKey` is misattributed — treat
with suspicion. (2) Does the finding's actor (IAM user, source IP,
parent process) appear in another finding in the same time window?
Correlated findings across families (e.g., a ConsoleLogin success
followed by a Persistence:IAMUser finding) are a kill-chain signature;
either alone might be noise, together they are almost certainly a
compromise. (3) What does the operator's environment say? The trusted
IP list, the IAM role name, and the deployment pipeline pattern are the
three highest-signal contextual inputs. A finding matching all three is
almost certainly a false positive; matching none is almost certainly a
true positive; the middle case is where senior judgment matters most.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **GuardDuty Runtime Monitoring (2024-2025):** GA for EC2, ECS
  (incl. Fargate), and EKS. The SSM-managed GuardDuty Security Agent
  reports process/network/module telemetry. Findings of the form
  `Runtime:EC2/ProcessA`, `Runtime:ECS/ProcessA`, `Runtime:EKS/ProcessA`
  require the agent installed and feature enabled per detector. Verify
  `aws guardduty list-features` shows Runtime Monitoring ENABLED.

- **GuardDuty EKS Protection (2024-2025):** Adds EKS audit-log
  monitoring alongside Runtime Monitoring. Findings attribute to the
  cluster via `resource.eksClusterDetails` and
  `resource.containerDetails` — distinguish audit-log findings (K8s API
  abuse) from Runtime findings (process behaviour). New K8s types
  include `UnauthorizedAccess:Kubernetes/SuccessfulAnonymousAccess`.

- **GuardDuty Malware Protection (2024-2025):** Scans EBS snapshots
  and S3 objects on-demand or via EventBridge. `aws malware-scan
  start-malware-scan` is the primary CLI. Scans are point-in-time — a
  clean scan does not prove the resource is malware-free in perpetuity.
  Malware Protection for S3 (GA 2024) auto-scans new objects on
  enabled buckets.

- **GuardDuty cross-account suppression (2024):** In Organizations
  with delegated admin, suppression filters created by the admin
  account propagate to member accounts — use the admin account for
  global rules.

- **GuardDuty RDS Protection (2024-2025):** GA, monitors RDS login
  anomalies (`UnauthorizedAccess:RDS/BruteForce`). VPC Flow Logs and
  RDS PostgreSQL/MySQL logs are the corroborating surfaces.

- **GuardDuty General Bucket Monitoring for S3 (2024):** Extended
  detection beyond Public Bucket Access — includes data-pattern
  exfiltration on private buckets. Tune via the S3 feature on the
  detector.

