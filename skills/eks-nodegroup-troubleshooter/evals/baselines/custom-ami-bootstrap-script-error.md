# Baseline (no-skill) response: custom-ami-bootstrap-script-error

This file captures what a generic assistant produces WITHOUT the
eks-nodegroup-troubleshooter skill loaded.

---

Your custom AMI nodes are launching but not joining the EKS cluster.
The error shows that the bootstrap script is trying to connect to
the wrong API server endpoint. The user-data has 10.0.0.1 but the
actual EKS endpoint is different.

You should fix the --apiserver-endpoint in your user-data script to
use the correct EKS API server endpoint. Also check that the cluster
CA is correct and that the bootstrap.sh script exists on your custom
AMI. Make sure the nodes can reach the API server over the network.
