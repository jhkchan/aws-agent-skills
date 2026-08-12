# Baseline (no-skill) — vpc-endpoint-private-access

> This is the response a model produces **without** the skill
> definition. It creates the domain and repository but misses that
> TWO VPC endpoints are needed (api and repositories), the private
> DNS requirement (--private-dns-enabled), and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the domain and repository:

```bash
aws codeartifact create-domain --domain internal-registry
aws codeartifact create-repository --domain internal-registry --repository java-artifacts
```

Create a VPC endpoint:

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.codeartifact.repositories \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-aaa111 subnet-bbb222
```

That should be enough for private access.
