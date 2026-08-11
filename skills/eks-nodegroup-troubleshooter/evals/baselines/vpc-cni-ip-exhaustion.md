# Baseline (no-skill) response: vpc-cni-ip-exhaustion

This file captures what a generic assistant produces WITHOUT the
eks-nodegroup-troubleshooter skill loaded.

---

Your EKS pods are stuck Pending. The error says "insufficient IP
addresses" which means the cluster doesn't have enough IP addresses
for the pods. This is likely because the subnets are too small or
there are too many nodes consuming IPs.

You should try creating larger subnets or reducing the number of
pods per node. Also check if the VPC CNI is configured correctly.
You might need to look at the WARM settings or consider using a
different CNI plugin. If that doesn't work, try adding more nodes
or scaling up the cluster.
