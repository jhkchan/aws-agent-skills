# Error Handling (load on demand) — EKS Hybrid Node Deployer

Error-handling deep dives and API failure tables moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

### Node stuck in NotReady
- Check network path to control plane (latency, packet loss). Verify
  kubelet running (`systemctl status kubelet`). Check activation code
  not expired. Review kubelet logs for connection errors.

### Pod identity permission denied
- Verify pod identity agent running on the node. Check the association
  exists in the EKS API. Ensure service account name matches. Check the
  node's IAM role can assume the pod-level role.

### Node cannot pull images from ECR
- Verify network path to ECR (443/TCP). Check IAM role has
  `AmazonEC2ContainerRegistryReadOnly`. Verify on-prem firewall allows
  outbound 443 to ECR.

### SSM Session Manager cannot connect
- Verify SSM agent running on the node. Check node is registered as SSM
  managed instance. Verify network path to SSM endpoints (443/TCP).
  Check IAM role has `AmazonSSMManagedInstanceCore`.

### Activation code expired
- Re-generate via the EKS API. Update nodeadm config. Restart kubelet.
