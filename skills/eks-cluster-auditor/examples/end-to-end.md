# End-to-end usage scenario: eks-cluster-auditor

A walkthrough showing the skill auditing a production EKS cluster that
has a public API endpoint, disabled logging, and a node-role privilege
escalation — demonstrating priority-ordered classification, the empty-
CIDR trap, and the multi-finding remediation workflow.

## Input (user prompt)

> Review this EKS cluster before our compliance audit next week. The
> cluster runs our payment processing workloads.

```json
{
  "cluster": {
    "name": "prod-payments-eks",
    "version": "1.29",
    "status": "ACTIVE",
    "resourcesVpcConfig": {
      "endpointPublicAccess": true,
      "endpointPrivateAccess": true,
      "publicAccessCidrs": []
    },
    "logging": {
      "clusterLogging": [
        {"types": ["api","audit","authenticator","controllerManager","scheduler"], "enabled": false}
      ]
    }
  }
}
```

aws-auth ConfigMap mapRoles:

```json
[
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-node-role",
    "username": "*",
    "groups": ["system:masters"]
  },
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-admin-role",
    "username": "admin",
    "groups": ["system:masters"]
  }
]
```

Node security groups:

```json
[
  {
    "groupId": "sg-prod-node",
    "groupName": "prod-node-sg",
    "ipPermissions": [
      {"fromPort": 10250, "toPort": 10250, "ipProtocol": "tcp", "ipRanges": [{"cidrIp": "0.0.0.0/0"}]}
    ]
  }
]
```

Latest available EKS version: 1.32.

## Skill output

```text
CLUSTER: prod-payments-eks
VERDICT: PUBLIC_ENDPOINT
REASON: API server endpoint is public with unrestricted CIDR
(publicAccessCidrs is empty, which EKS treats as 0.0.0.0/0) — the
control plane is reachable from the internet (Step 1). Control-plane
logging is also fully disabled and the node IAM role is mapped to
system:masters with a wildcard username.
FINDINGS:
  - [PUBLIC_ENDPOINT] endpointPublicAccess: true with empty
    publicAccessCidrs (defaults to 0.0.0.0/0) — API server reachable
    from any IP on the internet (Step 1)
  - [LOGGING_DISABLED] All 5 control-plane log types are disabled (Step 2)
  - [CONFIG_GAP] Node IAM role eks-node-role mapped to system:masters
    with username "*" — privilege escalation: any pod on the node
    inherits cluster-admin (Step 3a)
  - [CONFIG_GAP] Node SG sg-prod-node allows inbound 0.0.0.0/0 on port
    10250 (kubelet) — kubelet API reachable from internet (Step 3b)
  - [OUTDATED] Cluster version 1.29 is N-3 from latest 1.32 — past
    end-of-standard-support (Step 4)
REMEDIATION:
  1. PUBLIC_ENDPOINT — Disable public endpoint:
     aws eks update-cluster-config --name prod-payments-eks \
       --resources-vpc-config endpointPublicAccess=false
     Verify VPN/bastion connectivity BEFORE this change.
  2. LOGGING_DISABLED — Enable all control-plane logs:
     aws eks update-cluster-config --name prod-payments-eks \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
  3. CONFIG_GAP (IAM) — Back up aws-auth, then remove node role from
     system:masters. Replace with standard node groups:
     kubectl get configmap aws-auth -n kube-system -o yaml > backup.yaml
     Then apply corrected mapRoles with eks-node-role in
     system:nodes + system:bootstrappers.
  4. CONFIG_GAP (SG) — Revoke 0.0.0.0/0 on port 10250:
     aws ec2 revoke-security-group-ingress --group-id sg-prod-node \
       --protocol tcp --port 10250 --cidr 0.0.0.0/0
  5. OUTDATED — Plan upgrade to 1.31 or 1.32 after fixing the above.
     Check add-on compatibility first.
```

## What the skill caught that a generic assistant misses

1. **The empty publicAccessCidrs trap.** A generic assistant sees
   `publicAccessCidrs: []` and may report "no CIDRs configured." The
   skill knows that EKS treats an empty list as `["0.0.0.0/0"]` — the
   API server is wide open despite the empty-looking list.

2. **Priority-ordered verdict.** A generic assistant lists issues in
   arbitrary order. The skill emits PUBLIC_ENDPOINT as the verdict
   because it is the highest-priority finding — the other four findings
   (LOGGING_DISABLED, two CONFIG_GAPs, OUTDATED) appear in FINDINGS
   but do not change the verdict.

3. **The node-role privilege escalation chain.** A generic assistant
   says "node role has system:masters, that's bad." The skill explains
   the full chain: node IAM role -> EC2 instance profile -> pod inherits
   IAM identity -> pod impersonates node's Kubernetes identity -> pod
   has cluster-admin. This is why it is a CONFIG_GAP, not just a note.

4. **The kubelet port 10250 exposure.** A generic assistant may
   overlook port 10250. The skill recognizes it as the kubelet API
   port and explains that exposing it to 0.0.0.0/0 expands the attack
   surface for kubelet CVE exploitation.

## Slash-command invocation

```
/aws:audit-eks-cluster
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit my EKS cluster before the compliance review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: eks-cluster-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit my EKS cluster"
# [Phase: Audit | Skills routed: eks-cluster-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the cluster posture:

```bash
# Verify public endpoint is disabled
aws eks describe-cluster --name prod-payments-eks \
  --query 'cluster.resourcesVpcConfig.{endpointPublicAccess:endpointPublicAccess,publicAccessCidrs:publicAccessCidrs}'

# Confirm logging is enabled
aws eks describe-cluster --name prod-payments-eks \
  --query 'cluster.logging.clusterLogging'

# Verify aws-auth ConfigMap
kubectl get configmap aws-auth -n kube-system -o yaml

# Check node security groups
aws ec2 describe-security-groups --group-ids sg-prod-node \
  --query 'SecurityGroups[0].IpPermissions'
```
