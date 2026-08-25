# Error Handling — Snowball Edge Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Error handling

### Job creation fails — S3 bucket not found
- The S3 bucket must exist before creating the job. Verify with
  `aws s3api head-bucket`. Create the bucket if needed, then retry.

### Device pairing fails — manifest mismatch
- The manifest is job-specific. Download the correct manifest from
  the AWS Snowball console for THIS job. Do not reuse manifests from
  other jobs.

### NFS mount fails — service not started
- Start the NFS service via `snowballEdge start-service --service-id nfs`
  after unlock. NFS does not auto-start.

### Data transfer is slow
- Use parallel copy threads (`xargs -P 16`) for NFS, or increase
  `--max-concurrent-requests` for the S3 adapter. Verify the network
  link speed (100 GbE is optimal; 1 GbE is a bottleneck).

### Cluster formation fails — nodes not visible
- Verify all nodes are on the same network with mutual visibility.
  Check firewall rules and subnet configuration. All nodes must be the
  same device type.
