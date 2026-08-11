# End-to-End Example: EKS Add-On Deployment

A walkthrough showing how to use the `eks-add-on-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning core EKS add-ons on a new production cluster. The
deployment needs:

- Cluster: `production-cluster` (EKS 1.30, ACTIVE)
- Add-ons: vpc-cni, coredns, kube-proxy
- vpc-cni IAM: IRSA with `AmazonEKS_CNI_Policy`
- vpc-cni config: `ENABLE_PREFIX_DELEGATION=true`
- Conflict resolution: `OVERWRITE` (clean install on new cluster)

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-eks-add-on
```

Then paste the requirements.

### Option B: Natural language

```
You: "Set up vpc-cni, coredns, and kube-proxy on production-cluster
      (K8s 1.30). Use IRSA for vpc-cni with ENABLE_PREFIX_DELEGATION.
      Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create eks add-on vpc-cni"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
EKS_ADDON: vpc-cni (version v1.18.1-eksbuild.3) on cluster production-cluster
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster: production-cluster — ACTIVE, Kubernetes 1.30
  [✓] Add-on type: vpc-cni
  [✓] Add-on version: v1.18.1-eksbuild.3 (compatible with K8s 1.30)
  [✓] Management mode: EKS-managed
  [✓] Conflict resolution: OVERWRITE
  [✓] Configuration values: {"env":{"ENABLE_PREFIX_DELEGATION":"true"}}
  [✓] IAM credential method: IRSA (role AmazonEKSVPCCNIRole)
  [✓] OIDC provider: present
  [✓] Auto Mode cluster: no (manual management)
  [✓] Hybrid Nodes: no
  [✓] Health: ACTIVE
  [✓] Tags: Environment=production
VERIFICATION_COMMANDS:
  aws eks describe-addon --cluster-name production-cluster --addon-name vpc-cni
  aws eks list-addons --name production-cluster
  kubectl get pods -n kube-system -l k8s-app=aws-node
  kubectl get ds -n kube-system
```

---

## Step 3 — Provisioning commands

```bash
CLUSTER_NAME=production-cluster
ACCOUNT_ID=123456789012

# Step 1: Create IRSA role for vpc-cni
OIDC_URL=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

# ... trust policy + role creation (see provisioning-cli-commands.md) ...

# Step 2: Create vpc-cni add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni \
  --addon-version v1.18.1-eksbuild.3 \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKSVPCCNIRole \
  --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true"}}' \
  --resolve-conflicts OVERWRITE

# Step 3: Create coredns add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name coredns \
  --addon-version v1.11.1-eksbuild.4 \
  --resolve-conflicts OVERWRITE

# Step 4: Create kube-proxy add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name kube-proxy \
  --addon-version v1.30.0-eksbuild.3 \
  --resolve-conflicts OVERWRITE
```

---

## Step 4 — Post-deployment verification

```bash
# Verify all add-ons are ACTIVE
aws eks list-addons --name production-cluster --output table

# Verify vpc-cni status and config
aws eks describe-addon \
  --cluster-name production-cluster \
  --addon-name vpc-cni \
  --query 'addon.{Status:status,Version:addonVersion,Config:configurationValues}'

# Verify pods are running
kubectl get pods -n kube-system -l k8s-app=aws-node
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get pods -n kube-system -l k8s-app=kube-proxy
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Version compatibility | Latest or unspecified | Validated via describe-addon-versions | Incompatible versions crash pods |
| IRSA service account | Wrong or generic SA | aws-node in kube-system | Wrong SA → AccessDenied |
| Conflict resolution | Ignores (defaults to NONE) | OVERWRITE for clean install | Unresolved conflicts → DEGRADED |
| Configuration values | Sets via kubectl | Sets via --configuration-values | EKS-managed config must use API |
| Pod Identity vs IRSA | Picks one arbitrarily | Checks add-on compatibility | Not all add-ons support Pod Identity |

---

## Related artifacts

- **Skill definition:** `skills/eks-add-on-deployer/SKILL.md`
- **Version management detail:** `skills/eks-add-on-deployer/references/addon-version-management.md`
- **Provisioning CLI commands:** `skills/eks-add-on-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-eks-add-on.md`
- **Eval suite:** `skills/eks-add-on-deployer/evals/evals.json`
- **Legacy test cases:** `skills/eks-add-on-deployer/eval/test-cases.yaml`
