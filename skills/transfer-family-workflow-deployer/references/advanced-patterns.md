# Advanced patterns — transfer-family-workflow-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **Managed Workflows GA (2023-2024):** Step Functions-based managed
  workflows for automated pre/post file processing. Configurable steps:
  COPY, DELETE, TAG, CUSTOM (Lambda). On-exception steps for error
  handling.

- **AS2 Connectors GA (2023-2024):** B2B AS2 protocol support for
  EDI trading partner exchange. Certificate-based encryption and
  signing. Message Disposition Notifications (MDN) for delivery
  confirmation.

- **Structured JSON Logging (2023-2024):** Structured JSON logs to
  CloudWatch Logs with per-connection, per-file, and per-session
  details. Enables CloudWatch Logs Insights queries for audit and
  troubleshooting.

- **VPC_ENDPOINT Support (2023-2024):** PrivateLink-based VPC endpoint
  for private SFTP without NLB cost. Connect via VPC peering, TGW, VPN,
  or Direct Connect.

- **EFS Backing Storage (2023-2024):** Transfer Family now supports
  EFS as backing storage in addition to S3. Users can be mapped to EFS
  access points for file-system-based workflows.

- **Directory Service Integration (2024-2025):** Enhanced AWS Directory
  Service integration with automatic user provisioning and group-based
  home directory mapping.

- **Web App (2024-2025):** Managed web-based file browser for Transfer
  Family users, providing a GUI alternative to SFTP clients.
