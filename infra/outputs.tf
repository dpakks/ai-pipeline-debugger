output "webhook_url" {
  description = "API Gateway URL — paste this into GitHub webhook settings"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/webhook"
}

output "lambda_function_name" {
  description = "Lambda function name — used by deploy pipeline to update the function"
  value       = aws_lambda_function.debugger.function_name
}

output "ecr_repository_url" {
  description = "ECR repository URL — used by deploy pipeline to push Docker images"
  value       = aws_ecr_repository.app.repository_url
}