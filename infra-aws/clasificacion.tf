resource "aws_dynamodb_table" "nebula_scores" {
  name         = "nebula-scores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jugador"

  attribute {
    name = "jugador"
    type = "S"
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../serverless/lambda_function.py"
  output_path = "${path.module}/lambda_leaderboard.zip"
}

resource "aws_iam_role" "lambda_exec" {
  name = "nebula-leaderboard-lambda-role-${terraform.workspace}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_dynamo" {
  name = "nebula-leaderboard-dynamo-policy"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem", "dynamodb:Scan", "dynamodb:GetItem", "dynamodb:PutItem"]
        Resource = aws_dynamodb_table.nebula_scores.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "leaderboard" {
  function_name    = "nebula-leaderboard-${terraform.workspace}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  memory_size      = 256
  timeout          = 10

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.nebula_scores.name
    }
  }
}

resource "aws_lambda_function_url" "leaderboard" {
  function_name      = aws_lambda_function.leaderboard.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "public_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.leaderboard.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "public_invoke" {
  statement_id  = "AllowPublicInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.leaderboard.function_name
  principal     = "*"
}
