CI/CD and Infrastructure notes

GitHub Actions
- Workflow: `.github/workflows/ci.yml`
- Secrets to configure in repo settings (Settings -> Secrets):
  - `OPENAI_API_KEY` (if using OpenAI)
  - Docker registry credentials if you enable Docker builds

GitLab CI
- Config: `.gitlab-ci.yml`
- Set CI/CD variables in your GitLab project settings (CI/CD -> Variables)

Terraform
- Files live in `terraform/`.
- Before running, set AWS creds in your environment or use a shared credentials file.

Example terraform commands
```bash
cd terraform
terraform init
terraform plan -var='s3_bucket_name=my-unique-bucket-1234'
terraform apply -var='s3_bucket_name=my-unique-bucket-1234'
```

Security
- Never commit secrets to repo. Use platform secret stores.

Bitbucket Pipelines
- Config: `bitbucket-pipelines.yml` in repo root.
- Repository variables: set variables like `DOCKER_USER`, `DOCKER_PASSWORD`, `DOCKER_REGISTRY` in repository settings when enabling docker push steps.

Docker local build
------------------
Build the Docker image locally and run it:

```bash
docker build -t zclonic:latest .
docker run -p 5000:5000 --env FLASK_ENV=production zclonic:latest
```

If you bind-mount local code for development, remember to include dependencies in your environment or rebuild the image.
