output "state_bucket_name" {
  description = "S3 bucket name for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "lock_table_name" {
  description = "DynamoDB table name for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions — add this as AWS_ROLE_ARN secret in your repo"
  value       = aws_iam_role.github_actions.arn
}