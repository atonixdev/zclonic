# Zclonic — Enterprise AI Platform (Research Portal)

A polished Flask-based web app that demonstrates a small enterprise-focused AI platform: user accounts, an upload/analyze workflow, OAuth social login, and a modular dashboard with sections for settings, API keys, import history, and more.

This repository is intended as a starter for building secure, deployable enterprise tooling with a clean UI and a simple AI processing backend.

---

## Highlights

- Flask app with blueprint-based routes
- Session-based authentication and password hashing
- Social login via Authlib (GitHub, GitLab, LinkedIn, Facebook)
- SQLite for lightweight local persistence (expandable to Postgres)
- Responsive, accessible UI with a dashboard and sidebar
- Dockerfile + Compose, Kubernetes manifests (examples), and CI pipeline templates

---

## Quick start (development)

These steps assume you have Python 3.11+, pip, and a POSIX shell. Clone the repo, create a virtualenv, and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a minimal `config.py` (the repo includes a template) or set environment variables. For local development it's convenient to export env vars in your shell:

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export GITHUB_CLIENT_ID=<your-github-id>
export GITHUB_CLIENT_SECRET=<your-github-secret>
export GITLAB_CLIENT_ID=<your-gitlab-id>
export GITLAB_CLIENT_SECRET=<your-gitlab-secret>
export LINKEDIN_CLIENT_ID=<your-linkedin-id>
export LINKEDIN_CLIENT_SECRET=<your-linkedin-secret>
export FACEBOOK_CLIENT_ID=<your-facebook-id>
export FACEBOOK_CLIENT_SECRET=<your-facebook-secret>
export ZCLONIC_SECRET_KEY="change-this-to-a-secure-random-value"
```

Start the app:

```bash
flask run --host=0.0.0.0 --port=5000
```

Open `http://localhost:5000` in your browser.

---

## OAuth / Social login notes

1. Register apps for each provider and add the appropriate Redirect URI(s). The app uses the callback path `/auth/<provider>/callback`, for example:


2. Make sure the client ID and secret are set in environment variables or in `config.py`.

3. If you see an error like `The passed in client_id is invalid "None"`, it means the environment variable for that provider is not set or not loaded.


## LinkedIn App setup (step-by-step)

To enable LinkedIn social login you must register an app in the LinkedIn Developer portal and configure the correct redirect URI and scopes. Follow these steps:

1. Sign in to LinkedIn Developers: https://www.linkedin.com/developers/
2. Create a new app (My Apps → Create app). Fill in the required fields (App name, company, logo).
3. Under "Auth" (or "Products" → "Sign In with LinkedIn") add the Redirect URI you will use in your app. For this project the callback route is:

	- Local testing (HTTP): `http://localhost:5000/auth/linkedin/callback`
	- Production (HTTPS): `https://yourdomain.com/auth/linkedin/callback`

	The value you enter in LinkedIn must match exactly (scheme, domain, path). If you use a trailing slash in the LinkedIn app, make sure the app uses the same trailing slash.

4. Add the required OAuth scopes: at minimum add `r_liteprofile` and `r_emailaddress` (these let you fetch the user's name and email). If you need more profile fields, request additional scopes.

5. Copy the Client ID and Client Secret and set them in your environment (see `.env.example` below). If you see an error like `The passed in client_id is invalid "None"`, it means the app didn't find the Client ID in your environment.

6. Test the flow: Visit `/login` in your local app, click "LinkedIn" and complete the auth flow. If you encounter CORS or redirect mismatches, re-check the Redirect URI in the LinkedIn app settings.

Notes:
- Make sure your app is either in development with your LinkedIn account allowed to test, or submit it for LinkedIn review if you request extra scopes that require approval.
- For production, use HTTPS and a stable domain; LinkedIn will reject non-HTTPS redirect URIs in many cases.

---

## Environment example (`.env.example`)

Copy this file to `.env` (or export these variables in your environment) and fill in the values before running the app.

```env
# Flask
FLASK_APP=run.py
FLASK_ENV=development
ZCLONIC_SECRET_KEY=replace-with-a-secure-random-value

# OAuth / Social login (set these from each provider's developer portal)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
FACEBOOK_CLIENT_ID=
FACEBOOK_CLIENT_SECRET=

# Optional: OpenAI (for chat)
OPENAI_API_KEY=

# Optional: Sentence-transformers model override (local)
SENTENCE_MODEL=all-MiniLM-L6-v2
```
## Running with Docker

Build and run (example):

```bash
docker build -t zclonic:dev .
docker run -p 5000:5000 -e ZCLONIC_SECRET_KEY="yourkey" -e GITHUB_CLIENT_ID=... -e GITHUB_CLIENT_SECRET=... zclonic:dev
```

For production, use the provided `Dockerfile` and `compose.yaml` as a basis and secure secrets using Docker Compose secrets, Kubernetes Secrets, or a secret manager.

---

## Project layout

- `app.py`, `routes.py` — Flask app and routing
- `templates/` — Jinja2 templates
- `static/` — CSS/JS/assets
- `dbkamp/` — lightweight SQLite helpers
- `models/` — AI & chat mock/backend
- `k8kamp/`, `terraform/` — sample deployment manifests

---

## Security & production checklist

- Replace the default `ZCLONIC_SECRET_KEY` with a secure key
- Use PostgreSQL or MySQL for production
- Serve behind HTTPS and a reverse proxy (NGINX)
- Secure OAuth client secrets with a secret manager
- Add rate-limiting and monitoring

---

## Contributing

Contributions are welcome. Please open PRs against `main` and include a short description and tests where possible.


