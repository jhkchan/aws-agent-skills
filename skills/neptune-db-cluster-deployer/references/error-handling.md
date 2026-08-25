# Neptune DB Cluster Deployer — Error Handling

Provisioning API error deep dives moved verbatim from SKILL.md. Load on demand
 when a create/modify call fails.

## Cluster name already exists (`DBClusterAlreadyExists`)

### Cluster name already exists (`DBClusterAlreadyExists`)

- If config matches intent: skip to verification, emit READY_TO_DEPLOY.
- If config differs: mutable settings (instance class, parameter group,
  snapshot retention, security groups) change via `modify-db-cluster`.
  Engine version, storage encryption, and VPC/subnet placement CANNOT
  be changed — those require a new cluster + snapshot/restore.

### Multi-AZ create fails (`DBSubnetGroup does not span multiple AZs`)

**Fix:** add subnets in different AZs via `modify-db-subnet-group`,
then verify distinct `AvailabilityZone` values via
`aws ec2 describe-subnets`.

### IAM auth fails (`AccessDeniedException` from `neptune-db:Connect`)

**Fix:** add `neptune-db:Connect` on
`arn:aws:neptune:<region>:<account>:cluster/<name>` to the IAM
principal's policy; verify the client driver refreshes SigV4 tokens
(~15 min lifetime).

### Loader fails (`Loader could not assume role`)

**Fix:** verify the role trust policy includes `rds.amazonaws.com` and
that the bucket is in the same region as the cluster.
