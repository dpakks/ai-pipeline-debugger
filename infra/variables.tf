variable "project_name" {
  description = "Project name used for naming all resources"
  type        = string
  default     = "cicd-debugger"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "bedrock_model_id" {
  description = "AWS Bedrock model ID for LLM"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "github_webhook_secret" {
  description = "Secret token to validate incoming GitHub webhooks"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub Personal Access Token for reading logs and posting PR comments"
  type        = string
  sensitive   = true
}