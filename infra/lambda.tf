# -----------------------------------------------
# Lambda function — runs our Dockerized debugger
# -----------------------------------------------
resource "aws_lambda_function" "debugger" {
  function_name = var.project_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      BEDROCK_MODEL_ID      = var.bedrock_model_id
      GITHUB_WEBHOOK_SECRET = var.github_webhook_secret
      GITHUB_TOKEN          = var.github_token
      AWS_REGION_NAME       = var.aws_region
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_logs,
    aws_iam_role_policy.lambda_bedrock
  ]
}

# -----------------------------------------------
# CloudWatch log group — stores Lambda logs
# -----------------------------------------------
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}

# -----------------------------------------------
# Lambda permission — allows API Gateway to invoke it
# -----------------------------------------------
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.debugger.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook.execution_arn}/*/*"
}