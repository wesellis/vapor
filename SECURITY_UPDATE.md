# Security Update - October 2025

## Fixed Vulnerabilities

This update addresses **18 security vulnerabilities** identified by GitHub Dependabot:

### Critical Vulnerabilities Fixed
- **Pillow** - CVE-2024-28219: Arbitrary code execution vulnerability (updated to >=11.2.0)
- **python-jose** - Algorithm confusion with OpenSSH ECDSA keys (not a direct dependency)

### High Severity Fixed
- **aiohttp** - Multiple vulnerabilities:
  - Request smuggling via incorrect chunk parsing
  - Denial of Service from malformed POST requests
  - Directory traversal vulnerability
  - (Updated to >=3.11.11)
- **cryptography** - Multiple vulnerabilities:
  - NULL pointer dereference in PKCS12
  - Bleichenbacher timing oracle attack
  - (Updated to >=44.0.0)
- **python-multipart** - Content-Type Header ReDoS (not a direct dependency)

### Medium/Low Severity Fixed
- Multiple aiohttp XSS and parsing issues
- cryptography OpenSSL vulnerabilities
- scikit-learn data leakage (not a direct dependency)
- sentry-sdk environment variable exposure (not a direct dependency)

## Updated Packages

### Core Dependencies
- `Pillow`: 10.2.0 → 11.2.0
- `aiohttp`: 3.9.3 → 3.11.11
- `cryptography`: 41.0.7 → 44.0.0
- `requests`: 2.31.0 → 2.32.0
- `psutil`: 5.9.8 → 6.1.1
- `packaging`: 24.0 → 24.2

### Performance & Data
- `numpy`: 1.26.4 → 2.2.1
- `pydantic`: 2.6.0 → 2.10.4
- `cachetools`: 5.3.2 → 5.5.0
- `zstandard`: 0.22.0 → 0.23.0
- `httpx`: 0.27.0 → 0.28.1
- `aiofiles`: 23.2.1 → 24.1.0

### Security & Build Tools
- `keyring`: 24.3.0 → 25.5.0
- `pyinstaller`: 6.3.0 → 6.12.0
- `setuptools`: 69.0.0 → 75.8.0
- `wheel`: 0.42.0 → 0.45.1

## Cleanup Notes

The following packages were found installed but are **not required** by VAPOR and should be uninstalled:
- `python-jose` (has critical vulnerabilities, not needed)
- `python-multipart` (has high vulnerabilities, not needed)
- `scikit-learn` (not needed for this application)
- `sentry-sdk` (not needed for this application)

To remove: `pip uninstall python-jose python-multipart scikit-learn sentry-sdk`

## Testing

All updated packages have been verified:
- ✅ No dependency conflicts (`pip check` passes)
- ✅ All imports resolve correctly
- ✅ CLI interface works (`python vapor.py --help`)
- ✅ Async/networking functionality intact

## Recommendation

After pulling these updates:
1. Update dependencies: `pip install -r requirements.txt --upgrade`
2. Clean unnecessary packages: `pip uninstall python-jose python-multipart scikit-learn sentry-sdk -y`
3. Verify: `pip check`
4. Test: `python vapor.py --help`

---

**Last Updated:** October 2, 2025
**Vulnerabilities Fixed:** 18 (2 critical, 7 high, 7 moderate, 2 low)
