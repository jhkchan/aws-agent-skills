# Authentication and Access — Grafana Data Source Deployer

Deep reference on authentication options (IAM Identity Center vs SAML
SSO), user and group management, workspace permissions, API key
management, dashboard provisioning workflows, notification channels,
plugin management, and version control integration. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Authentication providers

### IAM Identity Center (AWS SSO)

IAM Identity Center is the simplest authentication option. It uses
AWS's built-in identity management.

**Configure at workspace creation:**

```bash
aws grafana create-workspace \
  --authentication-provider AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --workspace-name prod-observability \
  ...
```

**Assign users and groups after creation:**

```bash
# List current permissions
aws grafana list-permissions \
  --workspace-id "$WORKSPACE_ID" --region us-east-1

# Add a user as ADMIN
aws grafana update-permissions \
  --workspace-id "$WORKSPACE_ID" \
  --update-instruction-batch \
    "[{\"action\":\"ADD\",\"role\":\"ADMIN\",\"users\":[{\"id\":\"user-id\",\"ssoId\":\"user@example.com\"}]}]" \
  --region us-east-1

# Add a group as EDITOR
aws grafana update-permissions \
  --workspace-id "$WORKSPACE_ID" \
  --update-instruction-batch \
    "[{\"action\":\"ADD\",\"role\":\"EDITOR\",\"groups\":[{\"id\":\"group-id\",\"ssoId\":\"grafana-editors\"}]}]" \
  --region us-east-1
```

**Roles:**

| Role | Permissions |
|---|---|
| `ADMIN` | Full workspace access — manage data sources, users, settings |
| `EDITOR` | Create and edit dashboards, query data sources |
| `VIEWER` | View dashboards only (read-only) |

**Key:** with `SERVICE_MANAGED` permission type, users and groups are
managed through IAM Identity Center. With `CUSTOM`, you use Grafana's
built-in RBAC.

### SAML SSO

SAML SSO enables integration with external Identity Providers (Okta,
Azure AD, Google Workspace, etc.).

**Configure SAML after workspace creation:**

```bash
aws grafana update-workspace-saml-configuration \
  --workspace-id "$WORKSPACE_ID" \
  --saml-configuration '{
    "idpMetadata": {
      "url": "https://idp.example.com/saml/metadata"
    },
    "assertionAttributes": {
      "email": "email",
      "name": "displayName",
      "login": "email",
      "groups": "groups"
    },
    "roleValues": {
      "admin": "grafana-admins",
      "editor": "grafana-editors"
    },
    "automaticOrganizationAssignment": {
      "enabled": true,
      "organizationIds": {
        "grafana-admins": "org-admin",
        "grafana-editors": "org-editor"
      }
    }
  }' \
  --region us-east-1
```

**IdP configuration requirements:**

| Setting | Value |
|---|---|
| ACS URL | `https://g-<workspace-id>.grafana-workspace.<region>.amazonaws.com/login/saml/acs` |
| Audience | `https://g-<workspace-id>.grafana-workspace.<region>.amazonaws.com/` |
| NameID format | `emailAddress` or `unspecified` |
| Attribute: email | User email address |
| Attribute: displayName | User display name |
| Attribute: groups | Group memberships (comma-separated) |

**Assertion attribute mapping:**

```text
SAML Assertion → Grafana User:
  email attribute      → user email (required)
  name/displayName     → user display name
  login attribute      → login identifier (usually same as email)
  groups attribute     → group memberships for RBAC
```

### SAML SSO with IdP metadata XML (inline)

If you don't have a metadata URL, you can provide the XML inline:

```bash
aws grafana update-workspace-saml-configuration \
  --workspace-id "$WORKSPACE_ID" \
  --saml-configuration '{
    "idpMetadata": {
      "xml": "<EntityDescriptor xmlns=\"...\">...</EntityDescriptor>"
    },
    "assertionAttributes": {
      "email": "email",
      "name": "displayName",
      "login": "email"
    }
  }' \
  --region us-east-1
```

### Mutual exclusivity

A workspace can use EITHER IAM Identity Center OR SAML SSO, not both.
The authentication provider is set at workspace creation time. To
switch, you must create a new workspace.

## API key management

### Creating API keys

```bash
# Short-lived key for data source provisioning (1 hour)
DS_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "datasource-setup" \
  --key-role ADMIN \
  --seconds-to-live 3600 \
  --region us-east-1 \
  --query 'key' --output text)

# Long-lived key for CI/CD (24 hours)
CICD_KEY=$(aws grafana create-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "ci-cd-provisioning" \
  --key-role ADMIN \
  --seconds-to-live 86400 \
  --region us-east-1 \
  --query 'key' --output text)
```

### Key lifecycle

- **Maximum TTL:** 30 days (2,592,000 seconds).
- **One-time display:** the key value is shown ONLY at creation. It
  cannot be retrieved later.
- **Storage:** store the key in AWS Secrets Manager, Parameter Store,
  or a secure vault.
- **Rotation:** create a new key before the old one expires. Delete
  the old key.

```bash
# Delete an expired or unused key
aws grafana delete-workspace-api-key \
  --workspace-id "$WORKSPACE_ID" \
  --key-name "ci-cd-provisioning" \
  --region us-east-1
```

### Store API key in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name "grafana/${WORKSPACE_ID}/api-key" \
  --secret-string "$CICD_KEY" \
  --region us-east-1
```

## Dashboard provisioning

### Import a dashboard

```bash
curl -s -X POST "$ENDPOINT/api/dashboards/db" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

### Dashboard JSON structure

```json
{
  "dashboard": {
    "uid": "overview",
    "title": "Application Overview",
    "tags": ["production"],
    "timezone": "browser",
    "schemaVersion": 39,
    "panels": [
      {
        "id": 1,
        "title": "CPU Usage",
        "type": "timeseries",
        "datasource": {
          "type": "cloudwatch",
          "uid": "cloudwatch-prod-uid"
        },
        "targets": [
          {
            "queryMode": "Metrics",
            "metricName": "CPUUtilization",
            "namespace": "AWS/EC2"
          }
        ]
      }
    ]
  },
  "folderId": 0,
  "overwrite": true
}
```

**Critical:** the `datasource.uid` in each panel must match the UID of
the data source in the workspace. Mismatched UIDs cause "No data"
errors.

### Export a dashboard

```bash
curl -s "$ENDPOINT/api/dashboards/uid/overview" \
  -H "Authorization: Bearer $API_KEY" | \
  jq '.dashboard' > exported-overview.json
```

### Folder management

```bash
# Create a folder
curl -s -X POST "$ENDPOINT/api/folders" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Production Dashboards","uid":"prod-dashboards"}'

# Import dashboard into a specific folder
curl -s -X POST "$ENDPOINT/api/dashboards/db" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dashboard":{...},"folderUid":"prod-dashboards","overwrite":true}'
```

## Notification channels

### Grafana Alerting (unified)

Managed Grafana uses Grafana's unified alerting system with contact
points and notification policies.

**Create a Slack contact point:**

```bash
curl -s -X POST "$ENDPOINT/api/v1/provisioning/contact-points" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ops-team-slack",
    "type": "slack",
    "settings": {
      "url": "https://hooks.slack.com/services/xxx",
      "channel": "#ops-alerts",
      "title": "{{ template \"default.title\" . }}",
      "message": "{{ template \"default.message\" . }}"
    }
  }'
```

**Create an SNS contact point:**

```bash
curl -s -X POST "$ENDPOINT/api/v1/provisioning/contact-points" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sns-alerts",
    "type": "sns",
    "settings": {
      "topic": "arn:aws:sns:us-east-1:123456789012:grafana-alerts",
      "authProvider": "workspace"
    }
  }'
```

**Create a notification policy:**

```bash
curl -s -X PUT "$ENDPOINT/api/v1/provisioning/policies" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "routes": [
      {
        "receiver": "ops-team-slack",
        "object_matchers": [["severity", "=", "critical"]],
        "continue": false
      },
      {
        "receiver": "sns-alerts",
        "object_matchers": [["severity", "=", "warning"]],
        "continue": true
      }
    ]
  }'
```

## Plugin management

### Available plugins

Managed Grafana supports a curated set of plugins:

| Plugin | Type | Description |
|---|---|---|
| `cloudwatch` | data source | AWS CloudWatch metrics and logs |
| `prometheus` | data source | Prometheus / Amazon Managed Prometheus |
| `athena` | data source | Amazon Athena |
| `timestream` | data source | Amazon Timestream |
| `grafana-athena-datasource` | data source | Athena (newer version) |
| `elasticsearch` | data source | Amazon OpenSearch / Elasticsearch |
| `grafana-x-ray-datasource` | data source | AWS X-Ray |
| `redis` | data source | Redis |
| `postgres` | data source | PostgreSQL |
| `mysql` | data source | MySQL |

### Plugin restrictions

Managed Grafana does NOT support:
- Community plugins not on the AWS-approved list.
- Plugins requiring local file system access.
- Plugins requiring custom backend processes.

To check if a plugin is available:

```bash
curl -s "$ENDPOINT/api/plugins?type=datasource" \
  -H "Authorization: Bearer $API_KEY" | \
  jq '.[] | {name:name,id:id,enabled:enabled}'
```

## Version control integration (Enterprise)

Grafana Enterprise supports Git-based dashboard provisioning:

```bash
aws grafana update-workspace-configuration \
  --workspace-id "$WORKSPACE_ID" \
  --configuration '{
    "versionControl": {
      "provider": "github",
      "repository": "my-org/grafana-dashboards",
      "branch": "main",
      "directory": "/dashboards",
      "token": "ghp_xxx"
    }
  }' \
  --region us-east-1
```

With version control enabled:
- Dashboards committed to the Git repo are synced to the workspace.
- Changes made in the Grafana UI can be pushed back to Git.
- Enables GitOps workflows for dashboard lifecycle management.

**Note:** version control integration requires Grafana Enterprise.

## Common authentication pitfalls

1. **SAML IdP not configured before SAML workspace creation.** The
   workspace is created but users cannot log in. Configure the IdP
   first, then update the workspace SAML configuration.

2. **Wrong ACS URL in IdP.** The ACS URL must match exactly:
   `https://g-<id>.grafana-workspace.<region>.amazonaws.com/login/saml/acs`.
   Any mismatch causes SAML errors.

3. **API key used after expiration.** API keys have a TTL. If the key
   expires, API calls return 401 Unauthorized. Create a new key.

4. **Mixing SERVICE_MANAGED and CUSTOM.** SERVICE_MANAGED uses Identity
   Center groups. CUSTOM uses Grafana RBAC. Switching requires a new
   workspace.

5. **Not assigning any users.** After creating a workspace, assign at
   least one ADMIN user. Without an admin, the workspace is
   inaccessible.

## Terraform authentication example

```hcl
# SAML SSO workspace
resource "aws_grafana_workspace" "saml" {
  name                    = "enterprise-grafana"
  account_access_type     = "CURRENT_ACCOUNT"
  authentication_provider = "SAML"
  permission_type         = "CUSTOM"
  workspace_role_arn      = aws_iam_role.grafana.arn
  data_sources            = ["CLOUDWATCH", "ATHENA", "TIMESTREAM"]
}

# SAML configuration (must be applied after workspace is ACTIVE)
resource "aws_grafana_workspace_saml_configuration" "saml" {
  workspace_id = aws_grafana_workspace.saml.id

  idp_metadata_url = "https://idp.example.com/saml/metadata"

  assertion_attributes = {
    email = "email"
    name  = "displayName"
    login = "email"
    groups = "groups"
  }

  role_values = {
    admin  = "grafana-admins"
    editor = "grafana-editors"
  }
}

# User assignment (IAM Identity Center)
resource "aws_grafana_role_association" "admin" {
  workspace_id = aws_grafana_workspace.saml.id
  role         = "ADMIN"
  group_ids    = ["group-id-from-identity-center"]
}
```

## Expert heuristic: SAML SSO requires external IdP — moved from SKILL.md

```text
SAML SSO Setup Flow:
  1. Configure external IdP (Okta, Azure AD, etc.)
     → Create SAML application
     → Set ACS URL: https://<workspace-endpoint>/login/saml/acs
     → Set audience: https://<workspace-endpoint>/
     → Configure attribute mappings: email, displayName, groups
  2. Export IdP metadata (XML or metadata URL)
  3. Update Grafana workspace SAML configuration:
     aws grafana update-workspace-saml-configuration
       --workspace-id <id>
       --saml-configuration '{"idpMetadata":{"url":"..."},"assertionAttributes":{...}}'
  4. Test SAML login at https://<workspace-endpoint>/login/saml
```

**Key implication:** without the IdP metadata, SAML login fails. The
IdP must be configured first. This is a prerequisite — the workspace
cannot generate the IdP configuration for you.

## Step 6 — User management, notifications, plugins — moved from SKILL.md

**With IAM Identity Center, assign users/groups:**

```bash
aws grafana update-permissions \
  --workspace-id "$WORKSPACE_ID" \
  --update-instruction-batch \
    "action=ADD,role=ADMIN,groups=[{\"id\":\"group-id\",\"ssoId\":\"grafana-admins\"}]"
```

**With SAML SSO, users are mapped via assertion attributes.** The
`groups` attribute maps to Grafana roles via `roleValues` in the SAML
configuration.

**Create notification contact point (Slack example):**

```bash
curl -s -X POST "$ENDPOINT/api/v1/provisioning/contact-points" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"name":"ops-team-slack","type":"slack","settings":{"url":"https://hooks.slack.com/services/xxx","channel":"#ops-alerts"}}'
```

**List available plugins:**

```bash
curl -s "$ENDPOINT/api/plugins" -H "Authorization: Bearer $API_KEY" | jq '.[].id'
```

Managed Grafana restricts plugins to AWS-approved ones. Verify
availability before designing dashboards that depend on specific plugins.
