# Security Policy for `project_name`

We take the security of `project_name` seriously. This document outlines our security policies, supported versions, and how to responsibly disclose a vulnerability.

## Supported Versions

Please check the table below for the versions of `project_name` that are currently being supported with security updates.

| Version                         | Supported          |
| :------------------------------ | :----------------- |
| `{{current_major_version}}.x`   | :white_check_mark: |
| `< {{current_major_version}}.0` | :x:                |

*(Note: Replace the table contents with your actual versioning scheme once released.)*

## Reporting a Vulnerability

> [!IMPORTANT]
> **Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

If you discover a security vulnerability, please bring it to our attention right away using one of the following methods:

1. **GitHub Security Advisories (Preferred):** Use the "Report a vulnerability" button on the **[Security tab](https://github.com/%7B%7Borganization%7D%7D/%7B%7Bproject_name%7D%7D/security/advisories)** of this repository.
1. **Email:** Send your report directly to **[INSERT EMAIL ADDRESS OR SECURITY CONTACT]**. *(Optional: Encrypt your email using our PGP key: [INSERT PGP KEY LINK/FINGERPRINT])*

### What to Include in Your Report

To help us resolve the issue quickly, please include the following information:

- **Type of vulnerability** (e.g., XSS, SQLi, RCE, authorization bypass).
- **Detailed description** of the vulnerability and its potential impact.
- **Step-by-step instructions** to reproduce the issue.
- **Proof of Concept (PoC)** code or screenshots, if available.
- **Environment details** (e.g., version of `project_name`, OS, relevant configurations).

## Triage and Resolution Process

We will handle your report with strict confidentiality. Our process is as follows:

1. **Acknowledgment:** We will respond to your report as soon as possible, usually within **[INSERT NUMBER, e.g., 48] hours**.
1. **Triage:** We will investigate the issue and determine its validity and severity. We may contact you for further clarification.
1. **Fix:** If the vulnerability is verified, we will develop and test a patch.
1. **Disclosure:** We will coordinate with you to publicly disclose the vulnerability once a fix is released. We will publicly acknowledge your responsible disclosure, if you wish.

## Scope

**In Scope:**

- Vulnerabilities within the core `project_name` codebase.
- Security issues in our default configurations.

**Out of Scope:**

- Volumetric Denial of Service (DoS) attacks.
- Theoretical issues without a reproducible PoC.
- Vulnerabilities in third-party dependencies that are not exploitable through `project_name`.
- Missing security headers or best practices that do not lead to a direct exploit.

*(Note: We currently **[do/do not]** operate a bug bounty program. Disclosures are greatly appreciated but are not eligible for financial rewards at this time.)*
