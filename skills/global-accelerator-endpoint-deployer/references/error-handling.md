# Error Handling — Global Accelerator Endpoint Deployer

Error-handling deep dives moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### Endpoints always unhealthy
- Verify the endpoint resource exists and is healthy at the target group
  level. Check health check protocol, path, and port match.

### Traffic not reaching failover region
- The DR region's endpoints must be healthy. If all endpoints in the
  primary region are unhealthy but DR has no healthy endpoints, traffic
  is dropped.

### BYOIP accelerator creation fails
- Verify the BYOIP pool is in READY state and advertised. The
  provision-byoipcidr process can take 24-48 hours for ROA propagation.

