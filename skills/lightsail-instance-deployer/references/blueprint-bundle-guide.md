# Blueprints and Bundles Reference

Supplementary reference for the Lightsail Instance Deployer skill.
Use when selecting a blueprint (OS-only vs app+OS), sizing a bundle
(plan) for a workload, or verifying the app+OS minimum bundle
requirement.

## Blueprint catalog (2026, common)

### OS-only blueprints

| Blueprint ID | OS | Default user | Notes |
|---|---|---|---|
| `amazon_linux_2023` | Amazon Linux 2023 | `ec2-user` | Latest Amazon Linux. RPM-based. |
| `amazon_linux_2` | Amazon Linux 2 | `ec2-user` | Legacy; prefer 2023 for new deploys. |
| `ubuntu_22_04` | Ubuntu 22.04 LTS | `ubuntu` | Debian-based; broad community support. |
| `ubuntu_20_04` | Ubuntu 20.04 LTS | `ubuntu` | Older LTS. |
| `debian_12` | Debian 12 | `admin` | Stable, minimal. |
| `debian_11` | Debian 11 | `admin` | Older. |
| `open_suse_15` | openSUSE Leap 15 | `ec2-user` | RPM-based, YaST. |
| `freebsd_12` | FreeBSD 12 | `ec2-user` | Unix, ports tree. |
| `centos_9_stream` | CentOS Stream 9 | `ec2-user` | RPM-based. |

### App+OS blueprints

| Blueprint ID | Application stack | Minimum bundle | Default user |
|---|---|---|---|
| `wordpress` | WordPress + Apache + MySQL + PHP | `medium_3_0` (4 GB) | `bitnami` (or `ec2-user`) |
| `wordpress_multisite` | WordPress Multisite | `medium_3_0` (4 GB) | `bitnami` |
| `lamp_8` | Linux + Apache + MySQL + PHP 8 | `medium_3_0` (4 GB) | `bitnami` |
| `node_js` | Node.js (LTS) + npm | `medium_3_0` (4 GB) | `bitnami` |
| `django` | Django + Python + PostgreSQL/MySQL | `medium_3_0` (4 GB) | `bitnami` |
| `rails` | Ruby on Rails + Ruby + PostgreSQL | `medium_3_0` (4 GB) | `bitnami` |
| `ghost` | Ghost (Node.js blog) | `medium_3_0` (4 GB) | `bitnami` |
| `joomla` | Joomla CMS | `medium_3_0` (4 GB) | `bitnami` |
| `magento` | Magento e-commerce | `medium_3_0` (4 GB) | `bitnami` |
| `redmine` | Redmine project management | `medium_3_0` (4 GB) | `bitnami` |
| `gitlab` | GitLab CE | `large_3_0` (8 GB) | `bitnami` |
| `nginx_plesk` | Plesk hosting panel (license) | `large_3_0` (8 GB) | `admin` |
| `cpanel_whm` | cPanel + WHM (license) | `large_3_0` (8 GB) | `root` |

**App+OS stacks are typically Bitnami-packaged** — they ship with
the application, dependencies, and management scripts pre-configured.
The default admin password is generated at launch and surfaced in the
launch output; capture it immediately (not retrievable after).

## Bundle (plan) catalog (2026, Linux/FreeBSD)

| Bundle ID | RAM | CPU | SSD | Transfer | $/mo | Use case |
|---|---|---|---|---|---|---|
| `nano_3_0` | 512 MB | 1 | 20 GB | 1 TB | $3.50 | Dev/test only. Not for app+OS. |
| `micro_3_0` | 1 GB | 2 | 40 GB | 2 TB | $5 | Small OS-only app. |
| `small_3_0` | 2 GB | 2 | 60 GB | 3 TB | $10 | Small production OS-only. |
| `medium_3_0` | 4 GB | 2 | 80 GB | 4 TB | $20 | App+OS minimum. Mid production. |
| `large_3_0` | 8 GB | 4 | 160 GB | 5 TB | $40 | Mid-tier production. |
| `xlarge_3_0` | 16 GB | 8 | 320 GB | 7 TB | $80 | Production web/api. |
| `2xlarge_3_0` | 32 GB | 16 | 640 GB | 8 TB | $160 | Heavy production. |

**Windows bundles** use a different price scale (typically 50-100%
more for the same RAM/CPU). See `aws lightsail get-bundles --include-applicable-bundles-per-platform`.

**Database bundles** are a separate scale: `medium_3_0` database
bundle is NOT the same pricing as `medium_3_0` instance bundle.
Database bundles include managed MySQL/PostgreSQL with backups.

## Selecting the right bundle

### Decision tree

```
Workload type?
├─ OS-only custom stack?
│    ├─ Static site (nginx/apache, low traffic)?
│    │    └─ nano_3_0 (dev) → micro_3_0 (prod)
│    ├─ Web app (Node.js, Python, Go custom)?
│    │    └─ Profile app RAM at peak; add 50% headroom.
│    │       Typically micro_3_0 → small_3_0.
│    └─ API backend?
│         └─ small_3_0 (single instance) → medium_3_0 (HA pair)
│
├─ App+OS blueprint?
│    ├─ WordPress / LAMP / Node.js / Django / Rails / Ghost / Joomla / Magento?
│    │    └─ medium_3_0 minimum. large_3_0 for production under load.
│    └─ GitLab / Plesk / cPanel?
│         └─ large_3_0 minimum. xlarge_3_0 for production.
│
└─ HA production?
     └─ Prefer 2x medium_3_0 behind a Lightsail LB over 1x xlarge_3_0.
        The HA pair survives AZ failure; the single large instance does not.
```

### Common mistakes

- **Choosing `nano_3_0` for an app+OS blueprint.** The blueprint
  installs, but the stack OOMs under any non-trivial load. Always
  use the vendor minimum (`medium_3_0` for most app+OS).
- **Choosing `2xlarge_3_0` for a single-instance "production" deploy.**
  No HA — the instance is a single point of failure. Prefer 2x
  `large_3_0` behind a Lightsail LB.
- **Forgetting data transfer overage.** A `nano_3_0` instance with
  1 TB transfer that serves 2 TB outbound incurs ~$90 in overage
  ($0.09/GB * 1000 GB). Front cacheable content with a Lightsail
  distribution.
- **Ignoring snapshot storage cost.** A `2xlarge_3_0` snapshot (640 GB)
  costs ~$32/month at $0.05/GB-month. Review retention for large
  bundles; 7 days may be enough (vs. 30 days for compliance archives).

## User data (cloud-init) patterns

### LAMP stack customization (override default PHP config)

```bash
#!/bin/bash
# Override PHP memory limit (default is 128M; increase for production)
sed -i 's/memory_limit = 128M/memory_limit = 512M/' /opt/bitnami/php/etc/php.ini
/opt/bitnami/ctlscript.sh restart apache
```

### OS-only bootstrap (install nginx)

```bash
#!/bin/bash
apt-get update
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx
```

### App+OS WordPress (capture admin password to a file)

```bash
#!/bin/bash
# The default admin password is in /home/bitnami/bitnami_application_password
# Save it to a secure location (or send to Secrets Manager)
cat /home/bitnami/bitnami_application_password > /tmp/wp-admin-password.txt
chmod 600 /tmp/wp-admin-password.txt
```

## Firewall rule patterns

| Pattern | Rules | Use case |
|---|---|---|
| Public web server | 22 from corporate CIDR; 80, 443 from 0.0.0.0/0 | Default for LAMP, WordPress. |
| Internal API | 22 from corporate CIDR; 443 from corporate CIDR | Internal-facing API; no public web. |
| Bastion / jump host | 22 from corporate CIDR only | No web ports. Used to reach private instances. |
| Database | 3306 (MySQL) from Lightsail LB and app instance CIDRs | Private database; no public access. |
| Game server | 22 from corporate CIDR; game port (e.g., 27015) from 0.0.0.0/0 | Multiplayer game server. |

**Anti-pattern:** NEVER expose 3306 (MySQL) or 5432 (PostgreSQL) to
0.0.0.0/0. Tighten to the Lightsail LB and app instance CIDRs only.

## SSH access

Each region has one default Lightsail SSH key pair. Download once:

```bash
aws lightsail download-default-key-pair --region us-east-1 > lightsail-us-east-1.pem
chmod 600 lightsail-us-east-1.pem
ssh -i lightsail-us-east-1.pem <user>@<static-ip>
```

| Blueprint | Default SSH user |
|---|---|
| Amazon Linux | `ec2-user` |
| Ubuntu | `ubuntu` |
| Debian | `admin` |
| App+OS (Bitnami) | `bitnami` |
| Plesk / cPanel | `admin` / `root` |

For custom keys, upload via the Lightsail console or
`aws ec2 import-key-pair` (Lightsail uses EC2 key pairs under the hood).
