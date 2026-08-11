# Eval: dashboard-portal-sso

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — SSO portal with Identity Center, project, dashboard, threshold alarm with duration, access policy

## Prompt

Create a SiteWise project "Plant Monitoring" and portal "Acme Plant
Portal" with SSO auth mode (Identity Center instance ssoins-12345).
Role arn:aws:iam::123456789012:role/SiteWisePortal. Asset model
"Compressor" with measurement Pressure (DOUBLE, kPa) and alarm
HighPressure (Pressure GT 800 for 10 minutes). Dashboard "Compressor
Overview" in the project. Assign group
arn:aws:iam::123456789012:group/Operators as VIEWER on the project.
Account 123456789012. Tags: Environment=production.
