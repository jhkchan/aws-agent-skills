# Error Handling (load on demand) — Directory Service Deployer

Provisioning failure deep dives moved verbatim from SKILL.md.
The STRICT output contract and primary worked example remain in SKILL.md.

---

## Error handling (moved from SKILL.md)

### Directory stuck in CREATING state
- Creation takes 20-60 minutes. If it exceeds expected time, check
  subnet configuration, VPC DNS settings, and IAM permissions.

### Trust stuck in CREATING or FAILED state
- DNS conditional forwarders not configured or incorrect. Verify DNS
  resolution works between domains before creating the trust. Also
  verify network connectivity over required AD ports.

### LDAPS not working despite being enabled
- Certificate may have expired or CA chain not trusted. Verify
  certificate validity, check `DaysToExpiry` in ACM, ensure the
  issuing CA is in the client's trusted root store.

### AD Connector authentication failures
- On-prem AD unreachable (VPN/DX down) or DNS server IPs incorrect.
  Verify network connectivity and confirm correct IPs.

### IAM Identity Center SSO not working
- Directory not connected or IAM Identity Center pointing to wrong
  directory. Verify directory is ACTIVE and check user/permission
  set assignments.
