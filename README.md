# AI Pipeline Debugger

An AI-powered bot that automatically diagnoses CI/CD pipeline failures and posts root-cause analysis with suggested fixes directly on your GitHub Pull Requests.

No UI. No dashboard. Just a silent backend service that wakes up when a build fails, figures out what went wrong, and tells you how to fix it.

![Bot in action](https://img.shields.io/badge/status-live-brightgreen) ![AWS](https://img.shields.io/badge/cloud-AWS-orange) ![Terraform](https://img.shields.io/badge/IaC-Terraform-purple) ![Docker](https://img.shields.io/badge/container-Docker-blue)

---

## Demo

When a pipeline fails, the bot posts a comment like this on your PR:

> **🔍 CI/CD Pipeline Failure Diagnosis**
>
> **Root Cause** — The workflow attempts to install a non-existent npm package that doesn't exist in the npm registry, causing npm install to fail with a 404 error.
>
> **Fix** — Replace the package name with a valid one or add error handling.
>
> **Prevention** — Validate package names before committing workflows.

---

## How It Works

```
Developer pushes code
       │
       ▼
GitHub Actions (lint → test → docker build → push ECR → deploy)
       │
       ▼ (on failure)
GitHub Webhook
       │
       ▼
API Gateway → Lambda (Dockerized) → AWS Bedrock (Claude)
       │
       ▼
PR Comment (root cause + suggested fix)
```

1. Developer pushes code to GitHub
2. GitHub Actions pipeline runs (lint → test → build → deploy)
3. Pipeline fails
4. GitHub fires a webhook to our API Gateway endpoint
5. AWS Lambda (running as a Docker container) pulls the failure logs
6. Logs are cleaned, parsed, and sent to Claude via AWS Bedrock for analysis
7. Bot posts a structured diagnosis with root cause, fix, and prevention tips as a PR comment
8. Developer reads, fixes, pushes — cycle restarts

---

## Tech Stack

| Technology | Role |
|---|---|
| **GitHub Actions** | CI/CD orchestration — two pipelines: infra (Terraform) and deploy (Docker → ECR → Lambda) |
| **Docker** | Multi-stage containerization — optimized production images for Lambda deployment |
| **AWS Lambda** | Serverless compute — runs the debugger on demand, scales to zero when idle |
| **API Gateway** | Public HTTPS endpoint for receiving GitHub webhooks |
| **AWS ECR** | Private Docker image registry with lifecycle policies and vulnerability scanning |
| **AWS Bedrock** | Managed LLM access — Claude for intelligent log analysis, no API keys to manage |
| **Terraform** | Infrastructure as Code — provisions and manages all AWS resources |

> **Adapter pattern:** The LLM layer is isolated in a single file (`llm_client.py`). To switch from Bedrock/Claude to any other provider, only that file changes. Everything else stays untouched.

---

## Architecture Decisions

- **Serverless-first** — Lambda + API Gateway means zero cost when idle, instant scale when needed. No servers to patch or manage.
- **Container-based Lambda** — Docker image instead of zip deployment for reproducible, portable builds with consistent behavior across local and production environments.
- **Multi-stage Docker builds** — Separates build dependencies from runtime, producing slim ~100MB images for faster Lambda cold starts.
- **Infrastructure as Code** — Every AWS resource is defined in Terraform, version controlled, and reproducible. One `terraform apply` recreates the entire stack.
- **Separated CI/CD pipelines** — Infrastructure changes and application changes trigger independent pipelines, preventing unnecessary deployments.
- **Webhook signature verification** — Every incoming request is validated using HMAC-SHA256 to ensure it originated from GitHub. Timing-safe comparison prevents side-channel attacks.
- **Graceful failure** — If the LLM call fails, the bot still posts a comment explaining the error instead of failing silently.

---

## Project Structure

```
ai-pipeline-debugger/
│
├── bootstrap/                  # One-time manual Terraform (S3, DynamoDB, IAM)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
├── infra/                      # Main infra (automated via GitHub Actions)
│   ├── main.tf                 # Provider config and S3 backend
│   ├── lambda.tf               # Lambda function with Docker image
│   ├── api_gateway.tf          # HTTP API, route, integration, and stage
│   ├── ecr.tf                  # Container registry with lifecycle policy
│   ├── iam.tf                  # Least-privilege IAM roles and policies
│   ├── variables.tf
│   └── outputs.tf
│
├── app/                        # Lambda application
│   ├── handler.py              # Entry point — receives webhook, orchestrates everything
│   ├── github_client.py        # GitHub API — fetches logs, posts PR comments
│   ├── log_parser.py           # Cleans and structures raw logs for the LLM
│   ├── llm_client.py           # AWS Bedrock adapter — swappable LLM integration
│   ├── prompt_builder.py       # Constructs structured prompts with logs and diff context
│   └── requirements.txt
│
├── Dockerfile                  # Multi-stage build for Lambda container image
├── docker-compose.yml          # Local development and testing
│
├── .github/workflows/
│   ├── infra.yml               # Terraform plan on PR, apply on merge
│   └── deploy.yml              # Lint → test → Docker build → push ECR → deploy Lambda
│
├── tests/
│   ├── test_handler.py         # Webhook parsing, signature verification, orchestration
│   ├── test_log_parser.py      # Log cleaning, extraction, truncation
│   └── test_prompt_builder.py  # Prompt structure and content validation
│
└── README.md
```

---

## Setup

### Prerequisites
- AWS account with CLI configured
- GitHub repository with Actions enabled
- Docker installed
- Terraform installed

### 1. Bootstrap (one-time, manual)
```bash
cd bootstrap
# Create terraform.tfvars with your github_org and github_repo
terraform init
terraform apply
```
Creates the S3 state bucket, DynamoDB lock table, and GitHub Actions IAM role via OIDC.

### 2. Configure GitHub Secret
Add to your repo (Settings → Secrets → Actions):
- `AWS_ROLE_ARN` — IAM role ARN from bootstrap output

### 3. Initial deployment
```bash
# Create ECR and other infra (comment out Lambda initially)
cd infra
terraform init
terraform apply

# Build and push Docker image
docker buildx build --platform linux/amd64 --provenance=false -t <ECR_URL>:latest .
docker push <ECR_URL>:latest

# Uncomment Lambda and apply
terraform apply
```

### 4. Configure GitHub Webhook
Add webhook in repo Settings → Webhooks:
- **URL:** API Gateway URL from Terraform output
- **Content type:** `application/json`
- **Secret:** Your webhook secret
- **Events:** Workflow runs only

### 5. Push and CI/CD takes over
From this point on, every push to main automatically builds, tests, and deploys.

---

## Local Development

```bash
# Start the Lambda emulator
docker compose up

# Send a test webhook
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d '{"headers": {...}, "body": "..."}'
```

---

## License

MIT
