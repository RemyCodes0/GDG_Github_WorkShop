# Security Policy

## Reporting a vulnerability

Please do not open a public issue for security problems.

Email the GDG on Campus AUB Software Development Team lead at **lmm46@mail.aub.edu** with:

* what you found and where (file, endpoint, or page)
* steps to reproduce it
* what an attacker could do with it

We aim to reply within 7 days and will credit you in the fix unless you prefer otherwise.

## Automated scanning

Every pull request, every push to `main`, and a weekly Monday run go through
[`.github/workflows/security.yml`](.github/workflows/security.yml):

| Check | Tool | Fails the build when |
| --- | --- | --- |
| Code analysis | CodeQL (Python and JavaScript, `security-extended` queries) | a security issue is found in the code |
| Python packages | `pip-audit` on `Backend/requirements.txt` | a dependency has a known vulnerability |
| npm packages | `npm audit` | a runtime dependency has a high or critical vulnerability (dev tooling only warns) |
| Committed secrets | Gitleaks over the full history | a password, token, or key is found in a commit |
| Django settings | `manage.py check --deploy` | warns about missing production hardening (HTTPS, secure cookies, HSTS) |
| New dependencies | Dependency Review | a pull request adds a package with a high or critical vulnerability |

[Dependabot](.github/dependabot.yml) opens weekly pull requests for pip and npm updates and monthly ones for GitHub Actions.

CodeQL results appear under the repository's **Security > Code scanning** tab.

## Rules for contributors

* Never commit `.env`, passwords, API keys, or tokens. Use `.env.example` with placeholder values.
* If you commit a secret by accident, tell a maintainer right away. Rotating the secret matters more than deleting the commit.
* Prefer well maintained packages and pin version ranges in `requirements.txt` and `package-lock.json`.
