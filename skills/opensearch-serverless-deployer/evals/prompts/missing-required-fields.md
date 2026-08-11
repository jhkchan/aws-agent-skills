# Eval prompt: missing-required-fields

Design a deployment plan for an OpenSearch Serverless collection. Emit
the standard VERDICT block.

Requirements:

- Collection name: prod-data
- The user wants to store and search data in OpenSearch Serverless.

The user did not specify:

- Collection type (SEARCH / TIMESERIES / VECTORSEARCH)
- Encryption requirement (AWS-owned key vs customer-managed KMS)
- Network requirement (public vs VPC)
- OCU floor or capacity expectations
- Standby replicas preference
- Data access principals (IAM roles that need access)
- Whether SAML authentication is needed

The user expects the skill to identify what is missing and list the
required fields before producing a deployment plan.
