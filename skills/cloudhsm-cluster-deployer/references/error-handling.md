# Error Handling — CloudHSM Cluster Deployer

Error-handling deep dive moved out of the SKILL.md body for progressive disclosure: API error codes, stuck-state remedies, and recovery paths. Loaded on demand by the skill.

---

## Error handling

### create-cluster fails with CloudHsmAccessDeniedException
- Caller missing `cloudhsm:CreateCluster` or the
  AWSServiceRoleForCloudHSM service-linked role. Recreate via IAM.

### HSM stuck in CREATE_IN_PROGRESS
- Poll `describe-clusters`. If >30 min, the AZ may lack capacity.
  Try a different AZ in the cluster's subnet list.

### initialize-cluster fails with CloudHsmInvalidStateException
- The CSR hasn't been emitted yet (first HSM not ACTIVE). Wait for
  first HSM to reach ACTIVE before fetching the CSR.

### CO login fails with HSM error
- Wrong CO password, or the cluster's customer CA bundle isn't on
  the client host. Verify the CA bundle path
  (`/opt/cloudhsm/etc/customerCA.crt`) and password.

### Cross-region copy fails with ValidationException
- Destination region not enabled for CloudHSM. Enable via
  `cloudhsmv2 put-allow-destination-region` (or console).

### HSM in degraded state
- Create a replacement HSM in the same cluster (different AZ if the
  AZ is down), wait for ACTIVE + sync, then delete the degraded
  HSM.

### Want to change the customer CA
- Activation is one-time. To change CAs, restore from backup into a
  new cluster under the new CA.
