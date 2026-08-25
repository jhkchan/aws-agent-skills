
<!-- Moved verbatim from SKILL.md (eks-security-optimizer) — progressive-disclosure restructure, lines 114-133 -->

## Mindset — four principles

EKS security optimization is a defense-in-depth exercise, not a single
fix. The goal is to close the highest-severity gaps across all eight
dimensions — not to achieve perfect security on one dimension while
leaving others open.

Four principles guide every recommendation:

- **IAM is the root of trust.** If every pod uses the node IAM role,
  pod-level security controls (PSA, network policies) are bypassable.
  IRSA or Pod Identity is the foundation; everything else builds on it.
- **Default deny is the network baseline.** The Kubernetes default of
  allow-all east-west traffic is unacceptable in production. Every
  namespace should have a default-deny network policy with explicit
  allow rules for required flows.
- **Admission control is policy-as-code.** OPA Gatekeeper or Kyverno
  enforces security policies at admission time — before a pod is
  created. This prevents misconfigured workloads from ever running.
- **Runtime detection is the last line of defense.** GuardDuty EKS
  runtime monitoring detects lateral movement, credential theft, and
  anomalous process execution that network and admission controls miss.

<!-- Moved verbatim from SKILL.md (eks-security-optimizer) — progressive-disclosure restructure, lines 185-266 -->

## Step 0 — non-obvious behaviours that change the recommendation

- **PSA replaced PSP, not extended it.** PodSecurityPolicy was removed
  in Kubernetes 1.25. PSA is label-based (namespace labels) and enforced
  by the admission controller. It does NOT support custom policies —
  use Gatekeeper/Kyverno for custom rules.
- **EKS Pod Identity is the IRSA successor (2024).** Pod Identity uses
  a simpler agent-based approach instead of OIDC federation. For new
  clusters, prefer Pod Identity. For existing clusters, IRSA and Pod
  Identity can coexist during migration.
- **IMDSv2 hop-limit=1 blocks pod access.** The Instance Metadata
  Service is on the node network. Setting `HttpPutResponseHopLimit=1`
  prevents pods (which are one network hop away) from reaching IMDS.
  This is the most effective defense against SSRF-based credential theft.
- **KMS secrets encryption requires a new key for existing secrets.**
  Enabling KMS encryption on an existing cluster encrypts NEW secrets
  only. Existing secrets must be re-encrypted by rotating them.
- **Network policies require a CNI plugin.** The AWS VPC CNI does not
  implement Kubernetes NetworkPolicy. You must install Calico or Cilium
  for network policy enforcement.
- **ECR enhanced scanning requires Inspector enablement.** Basic scan
  uses open-source CVE databases. Enhanced scan uses Amazon Inspector
  for broader coverage including package and code vulnerabilities.
- **GuardDuty EKS runtime monitoring requires the EKS addon.** It is
  not sufficient to enable the GuardDuty detector — the
  `aws-guardduty-agent` addon must be installed on the cluster.
- **Audit log types are individually toggled.** The `logging` config
  has five types: api, audit, authenticator, controllerManager, scheduler.
  Each must be explicitly enabled. Missing `audit` logs means no
  record of API server requests.
- **API server private endpoint changes cluster networking.** Switching
  to private-only endpoint means kubectl must run from within the VPC
  (bastion, VPN, or Connected Tunnel). Plan the migration carefully.
- **kubelet anonymous auth must be explicitly disabled.** The default
  kubelet configuration on some AMIs allows anonymous access to the
  kubelet API. This must be disabled via `--anonymous-auth=false`.
- **PSA and OPA Gatekeeper overlap is NOT redundant — they serve
  different layers.** PSA enforces a fixed taxonomy (privileged,
  baseline, restricted) at the admission controller level with NO
  customization. Gatekeeper/Kyverno enforce custom policies (e.g.,
  "every pod must have a cost-center label," "images must come from
  approved registries"). Use BOTH: PSA for the standard pod-hardening
  floor, Gatekeeper for organization-specific rules. A common mistake
  is deploying Gatekeeper to enforce baseline security controls that
  PSA already covers — this doubles the admission latency with zero
  additional security. Rule: let PSA handle pod spec validation, let
  Gatekeeper handle cross-cutting governance (labels, registries,
  resource quotas).
- **IRSA token audience must match the IAM trust policy `sts:Audience`
  condition.** The OIDC token issued to a pod contains an audience
  (`aud`) field that defaults to `sts.amazonaws.com`. If the IAM role's
  trust policy specifies a custom audience condition
  (`"StringEquals": {"oidc.eks.region.amazonaws.com/id/XXX:aud":
  "my-custom-audience"}`), the pod's service account annotation MUST
  set `eks.amazonaws.com/audience` to the same value. A mismatch causes
  `AccessDenied` from STS with no obvious error trail — the pod appears
  healthy but every AWS SDK call fails silently. Expert rule: use the
  default audience (`sts.amazonaws.com`) unless you have a specific
  multi-cluster isolation requirement that demands custom audiences.
- **KMS key rotation does NOT re-encrypt existing Kubernetes secrets
  in-place.** When you rotate a KMS key (automatic annual rotation or
  manual), the KMS key material changes but existing ciphertext
  (already-encrypted secrets in etcd) is decrypted using the old key
  material and then re-encrypted with the new key material — BUT only
  on the NEXT write to that secret. Envelope decryption works because
  KMS retains the ability to decrypt with old key versions. The
  security improvement is forward-looking (new encrypt operations use
  the new key material), not retrospective. To force full re-encryption
  of all secrets after a key rotation, run:
  `kubectl get secrets -A -o json | kubectl replace -f -` which reads
  and re-writes every secret, triggering re-encryption with the current
  key material. Pods holding decrypted secrets in memory are unaffected;
  the re-encryption only matters for secrets at rest in etcd.
- **EKS API server audit log volume is a hidden CloudWatch cost.**
  Audit logging at the `api` and `audit` log types generates one log
  event per API server request. A busy production cluster (100+ nodes,
  frequent deployments, controllers polling) can generate 50-200 GB of
  audit logs per month in CloudWatch Logs. At $0.50/GB ingestion, this
  is $25-$100/month just for audit logs. The cost is NOT surfaced in
  the EKS console. Expert rules: (1) set a CloudWatch Logs retention
  period (30-90 days) to prevent unbounded growth; (2) if cost is
  prohibitive, enable only `audit` and `authenticator` log types
  (skip `api` if you have application-level audit logging); (3) export
  logs to S3 for long-term archival at 10x lower cost.

<!-- Moved verbatim from SKILL.md (eks-security-optimizer) — progressive-disclosure restructure, lines 713-731 -->

## Recent AWS features (2024-2026)

- **EKS Pod Identity (2024-2025):** Simpler alternative to IRSA using
  an agent-based approach. No OIDC provider required. Coexists with
  IRSA during migration.
- **Pod Security Admission (Kubernetes 1.25+, EKS):** Replaces
  PodSecurityPolicy. Label-based enforcement of privileged/baseline/
  restricted profiles.
- **GuardDuty EKS Runtime Monitoring (2024-2025):** Runtime threat
  detection for EKS via the `aws-guardduty-agent` addon. Detects
  credential theft, lateral movement, anomalous processes.
- **ECR Enhanced Scanning with Inspector (2024-2025):** Broader
  vulnerability coverage than basic scanning. Includes package and
  code-level vulnerabilities.
- **EKS Auto Mode (2024-2025):** Managed node pools with built-in
  security defaults (IMDSv2 enforced, latest AMI).
- **KMS secrets encryption on cluster creation (2024-2025):** Can now
  be specified at cluster creation time, not just via update-cluster-config.
- **VPC CNI network policy support (2024-2025):** VPC CNI now supports
  a subset of Kubernetes NetworkPolicy, reducing the need for Calico/
  Cilium for basic policies.

