# Advanced Patterns (load on demand) — EKS Cluster Auditor

Expert-knowledge deep dives, edge cases, appendices, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious EKS behaviors that change classification (moved from SKILL.md)

Each behavior below changes a verdict if ignored:

- **Empty `publicAccessCidrs` is NOT "no access."** When
  `endpointPublicAccess: true` and `publicAccessCidrs` is an empty list
  `[]`, EKS treats it as `["0.0.0.0/0"]` — the API server is wide open.
  Operators who set `[]` to "clear" the list actually leave public access
  unrestricted. Always treat an empty or absent `publicAccessCidrs` with
  `endpointPublicAccess: true` as PUBLIC_ENDPOINT.

- **`endpointPrivateAccess: true` + `endpointPublicAccess: true` is NOT
  private.** Both can be true simultaneously. The public endpoint remains
  accessible from the internet regardless of the private endpoint state.
  Only `endpointPublicAccess: false` removes the public attack surface.

- **Restricted CIDRs on the public endpoint are a valid control, not
  PUBLIC_ENDPOINT.** If `publicAccessCidrs` contains specific corporate
  CIDRs (e.g., `203.0.113.0/24`) and NOT `0.0.0.0/0`, the endpoint is
  network-scoped. This is acceptable — classify under later steps, not
  PUBLIC_ENDPOINT.

- **Control-plane logs are OFF by default.** Creating an EKS cluster does
  not enable any control-plane logging. All five log types (`api`, `audit`,
  `authenticator`, `controllerManager`, `scheduler`) must be explicitly
  enabled. The most common gap is operators assuming CloudTrail covers EKS
  control-plane activity — it does not. CloudTrail logs EKS **management
  API calls** (CreateCluster, UpdateCluster, etc.), not Kubernetes API
  calls (create pod, exec into container, etc.).

- **`api` and `audit` are the two log types that matter most.** `api`
  captures every Kubernetes API call; `audit` captures the Kubernetes audit
  log (who, what, when, allowed/denied). `authenticator` logs IAM-to-RBAC
  mapping decisions. `controllerManager` and `scheduler` are lower priority
  but should still be enabled for completeness. If only `controllerManager`
  and `scheduler` are disabled while `api`, `audit`, and `authenticator`
  are enabled, do NOT classify as LOGGING_DISABLED — note as a minor gap.

- **`system:masters` is Kubernetes root.** Any IAM principal mapped to the
  `system:masters` group bypasses all RBAC checks and has unrestricted
  access to every Kubernetes resource. Mapping the EKS **node IAM role**
  (the role attached to EC2 worker instances) to `system:masters` is a
  critical privilege escalation: every pod on that node inherits the
  node's IAM identity and can impersonate it to gain cluster-admin.

- **`username: "*"` in a mapRoles entry is a wildcard identity mapping.**
  It means every IAM principal matching the `rolearn` is mapped to the
  same Kubernetes identity. Combined with `system:masters`, this grants
  cluster-admin to every identity that can assume the role — including
  cross-account principals if the role trust policy allows it.

- **Access entries (EKS 1.29+) replace aws-auth ConfigMap.** When
  `authenticationMode` is `API` or `API_AND_CONFIG_MAP`, EKS uses native
  access entries instead of the ConfigMap. Audit `aws eks list-access-entries`
  and `aws eks describe-access-entry` instead of the ConfigMap. A cluster
  in `API_AND_CONFIG_MAP` mode uses BOTH — audit both surfaces.

- **Port 10250 (kubelet API) exposure is more dangerous than port 443.**
  The kubelet API on worker nodes accepts commands (exec, port-forward,
  logs) from the API server. If a node security group allows inbound
  `0.0.0.0/0` on 10250, an attacker on the internet can attempt direct
  kubelet API calls. While the kubelet requires authentication (webhook
  authz to the API server), exposing the port expands the attack surface
  and enables exploitation of kubelet CVEs.

- **EKS version lifecycle: standard support is ~14 months per minor
  version.** After standard support ends, the cluster enters extended
  support (3 months, with a per-cluster-hour surcharge). After extended
  support, AWS force-upgrades the cluster. For the OUTDATED threshold, use
  N-3: if the cluster is running a version 3 or more minor versions behind
  the latest available EKS version, it is past or approaching end-of-
  standard-support. Example: if latest is 1.32, then 1.29 and older are
  OUTDATED; 1.30 is N-2 (advisory); 1.31 is N-1 (current).

- **Fargate profiles do not have node IAM roles or security groups.**
  A Fargate-only cluster has no EC2 worker nodes, so the SG and node-IAM-
  role dimensions are N/A. Still audit endpoint, logging, version, and
  Fargate execution role permissions.

- **How to determine the latest available EKS version.** The input
  should state the latest version. If it does not, query it:
  `aws eks describe-addon-versions --query 'addons[].addonVersions[].compatibilities[].clusterVersion' --output text | sort -V | tail -1`
  or check the AWS EKS documentation release calendar. EKS typically
  supports 4 concurrent minor versions. Never guess the latest — an
  incorrect N-offset produces a false OUTDATED or false OK.

- **`publicAccessCidrs` accepts a maximum of 40 CIDR blocks.** Adding
  more silently fails with `InvalidParameterException`. Operators who
  try to allowlist many office CIDRs hit this limit and fall back to
  `0.0.0.0/0` — trading security for convenience. If more than 40
  CIDRs are needed, use a VPN or bastion with `endpointPublicAccess:
  false` instead.

- **The `aws-auth` ConfigMap is NOT reconciled by EKS.** It lives in
  etcd and is purely user-managed — EKS never writes to it after initial
  creation. If a managed node group adds nodes with a new IAM role, the
  ConfigMap is NOT updated automatically. Access entries (API mode), by
  contrast, are EKS-managed and reconcile automatically. This is a key
  reason to migrate from ConfigMap to access entries.

- **EKS auto-patches but never auto-upgrades minor versions.** A cluster
  at 1.28.2 may silently move to 1.28.3 (patch update within the same
  minor version), but will NEVER auto-upgrade to 1.29. Without a
  deliberate upgrade plan, clusters drift indefinitely. This is why the
  OUTDATED verdict exists — it catches silent drift.

- **Control-plane log delivery is asynchronous (1-5 minute delay).**
  During a security incident, the CloudWatch log stream lags behind real
  time. For real-time detection, pair control-plane logs with a SIEM or
  CloudWatch Alarm with a metric filter — do not rely on manual log
  inspection during an active incident.

- **Access entry trust policies can grant cross-account access.** When
  auditing access entries (`aws eks describe-access-entry`), check the
  `principalARN` for cross-account ARNs. An access entry mapping a
  foreign account role to `system:masters` is equivalent to a cross-
  account `aws-auth` ConfigMap entry — both are CONFIG_GAP.


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EKS Access Entries (2024-2025):** EKS Access Entries replace the `aws-auth` ConfigMap for IAM-to-Kubernetes authentication mapping. Auditors should verify that access entries are used instead of (or in addition to) the ConfigMap, and that no access entry maps a broad principal to `system:masters`. The ConfigMap approach is deprecated.
- **EKS Auto Mode (2024-2025):** EKS Auto Mode manages node provisioning, scaling, and lifecycle automatically. Auditors should note that Auto Mode changes the node audit surface — node security groups, AMI versions, and instance profiles are managed by EKS rather than custom node groups. Verify that Auto Mode configuration does not inadvertently create permissive security groups.
- **EKS Pod Identity (2024):** EKS Pod Identity provides IAM credentials to pods without OIDC trust policies. Auditors should verify that Pod Identity associations use scoped IAM roles and that the EKS Pod Identity Agent addon is installed and up-to-date.
- **EKS Hybrid Nodes (2025):** EKS now supports on-premises nodes attached to EKS clusters. Auditors should verify that hybrid node security groups and IAM roles are scoped appropriately — hybrid nodes may have different network exposure than cloud-managed nodes.
- **Pod-level security:** Enhanced pod security standards (PSS) enforcement. Auditors should verify that PSS is set to `restricted` (not `baseline` or `privileged`) for production namespaces.
