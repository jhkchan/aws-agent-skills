# Error Handling — RDS Proxy Deployer

### Proxy status is Unavailable
- Secret format is wrong or IAM role cannot read the secret. Verify JSON
  keys and role permissions.

### Connections time out
- Database SG does not allow ingress from proxy SG. Add the ingress rule
  on the database port.

### Application gets no connection pooling benefit
- Application is connecting to the cluster endpoint. Update the
  connection string to the proxy endpoint.

### IAM auth fails
- TLS not enforced. IAM auth REQUIRES `--require-tls`.

### Proxy connections exhausted during spikes
- MaxConnectionsPercent too low. Increase it, or scale up the Aurora
  instance class/ACU.
