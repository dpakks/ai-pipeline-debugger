# -----------------------------------------------
# HTTP API — the public endpoint for GitHub webhooks
# -----------------------------------------------
resource "aws_apigatewayv2_api" "webhook" {
  name          = "${var.project_name}-webhook"
  protocol_type = "HTTP"
}

# -----------------------------------------------
# Integration — connects API Gateway to Lambda
# -----------------------------------------------
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.webhook.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.debugger.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# -----------------------------------------------
# Route — POST /webhook triggers the Lambda
# -----------------------------------------------
resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.webhook.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# -----------------------------------------------
# Stage — deploys the API with auto-deploy enabled
# -----------------------------------------------
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.webhook.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      errorMessage   = "$context.error.message"
    })
  }
}

# -----------------------------------------------
# CloudWatch log group for API Gateway access logs
# -----------------------------------------------
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 14
}