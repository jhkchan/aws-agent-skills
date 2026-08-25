# Portals Dashboards And Access — sitewise-asset-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Step 7 — Dashboards (project and portal)

SiteWise dashboards visualize asset property data. Dashboards live in
projects. Portals aggregate projects and provide web-based access.

**Create a project:**

```bash
PROJECT_ID=$(aws iotsitewise create-project \
  --project-name "Wind Farm Monitoring" \
  --portal-id "$PORTAL_ID" \
  --query 'projectId' --output text)
```

**Create a dashboard:**

```bash
DASHBOARD_ID=$(aws iotsitewise create-dashboard \
  --dashboard-name "Turbine WT-001 Overview" \
  --project-id "$PROJECT_ID" \
  --dashboard-definition file://dashboard-definition.json \
  --query 'dashboardId' --output text)
```

**Dashboard definition JSON** contains widget configurations (line
charts, bar charts, KPIs, status grids) bound to asset property IDs.

**Create a portal (requires Identity Center):**

```bash
PORTAL_ID=$(aws iotsitewise create-portal \
  --portal-name "Acme Wind Farm Portal" \
  --portal-contact-email "ops@acme.com" \
  --role-arn "$PORTAL_ROLE_ARN" \
  --portal-auth-mode "IAM" \
  --alarms-enabled \
  --query 'portalId' --output text)
```

**Critical:** portal creation requires an IAM role that SiteWise
assumes to read asset data on behalf of portal users. The role must
have `iotsitewise:BatchGetAssetPropertyAggregates`,
`iotsitewise:BatchGetAssetPropertyValue`, and
`iotsitewise:BatchGetAssetPropertyValueHistory` permissions.


## Step 10 — Identity Center for portal access

SiteWise portals use Identity Center (SSO) for user authentication when
`portalAuthMode` is `SSO`.

**Configure Identity Center for portal:**

```bash
# Portal with SSO auth mode
PORTAL_ID=$(aws iotsitewise create-portal \
  --portal-name "Acme Wind Farm Portal" \
  --portal-contact-email "ops@acme.com" \
  --role-arn "$PORTAL_ROLE_ARN" \
  --portal-auth-mode "SSO" \
  --query 'portalId' --output text)
```

**Assign users/groups to portal projects:**

```bash
# Assign a user or group to a project with a role
aws iotsitewise create-access-policy \
  --access-policy-identity '{
    "iam": {"arn": "arn:aws:iam::123456789012:role/SiteWisePortalViewer"}
  }' \
  --access-policy-permission '{
    "project": {"permission": "VIEWER", "projectId": "'"$PROJECT_ID"'"}
  }' \
  --access-policy-resource '{
    "portal": {"id": "'"$PORTAL_ID"'"}
  }'
```

**Project roles:** `ADMINISTRATOR` (full control), `EDITOR` (create/edit
dashboards), `VIEWER` (read-only).

**Critical:** portal access requires both an Identity Center user AND
an access policy. Without the access policy, the user can authenticate
but sees no projects.

