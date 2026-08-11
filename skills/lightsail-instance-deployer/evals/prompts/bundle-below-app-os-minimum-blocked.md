# Eval prompt: bundle-below-app-os-minimum-blocked

Design a deployment plan for a WordPress Lightsail instance. Emit
the standard VERDICT block.

Requirements:

- Instance name: prod-wp
- Blueprint: wordpress (app+OS)
- Bundle: nano_3_0 (512 MB RAM, 1 CPU, 20 GB SSD, 1 TB transfer) —
  chosen by the user for cost savings
- AZ: us-east-1a
- Static IP: required (prod-wp-ip allocated)
- DNS: zone blog.example.com
- Snapshots: automatic daily at 04:00 UTC

Existing-account context: the user is cost-conscious and selected
the smallest bundle to keep monthly spend under $5. The WordPress
blueprint installs on nano_3_0 — but MySQL and PHP-FPM together
exceed 512 MB under any non-trivial load. In testing, the user's
previous nano WordPress instance crashed daily during the morning
traffic spike (MySQL OOM). The user wants to try the same bundle
again with this new deploy.
