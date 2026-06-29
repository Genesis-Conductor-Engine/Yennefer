# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, email: security@diamondnode.example.com

Include:
- Type of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

## Security Best Practices

- Never commit API keys or secrets
- Use `.env` files (not committed)
- Keep dependencies updated
- Run security audits: `pip audit`, `npm audit`
- Use HTTPS for production deployments
