
<!-- Moved verbatim from SKILL.md (eks-upgrade-operator) — progressive-disclosure restructure, lines 138-163 -->

## Live-account pre-flight command gate

1. `aws eks describe-cluster --name <cluster>` — confirm `status:
   ACTIVE`; capture `version`, `platformVersion`, `addonsConfig`,
   `accessConfig.authenticationMode`, `computeConfig` (Auto Mode),
   `remoteNetworkConfig` (hybrid nodes).
2. `aws eks list-addons --cluster-name <cluster>` — list installed EKS
   add-ons.
3. `aws eks describe-addon --cluster-name <cluster> --addon-name
   <name>` per add-on — capture `addonVersion`, `status`,
   `configurationValues`.
4. `aws eks describe-addon-versions --kubernetes-version <target>` —
   list compatible add-on versions for the target Kubernetes.
5. `aws eks list-nodegroups --cluster-name <cluster>` — list all
   managed node groups.
6. `aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name
   <name>` per node group — capture `version`, `status`,
   `instanceTypes`, `subnets`, `scalingConfig`, `amiType`, `updateConfig`
   (maxUnavailable, maxSurge).
7. `kubectl get nodes -o wide` — verify all nodes are `Ready` and on the
   expected version.
8. `kubectl get poddisruptionbudgets --all-namespaces` — find PDBs that
   might block drain.
9. `kubectl get pods --all-namespaces --field-selector
   status.phase=Running` — sample workload; pair with `kubent` for
   deprecated API detection.
10. `kubectl get apiversions` — list all API groups/versions in use
    (for deprecated API scan).

